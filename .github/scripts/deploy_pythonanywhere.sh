#!/usr/bin/env bash
# Deploy su PythonAnywhere tramite API: carica i file cambiati e ricarica la web app.
#
# Variabili richieste:
#   PA_API_TOKEN    token API (Account -> API Token)
#   PA_USERNAME     username PythonAnywhere
#   PA_PROJECT_DIR  cartella del progetto sul server, es. /home/<username>/TodoApp
# Variabili opzionali:
#   PA_HOST         www.pythonanywhere.com (default) oppure eu.pythonanywhere.com
#   PA_DOMAIN       dominio della web app (default <username>.pythonanywhere.com)
#   BEFORE_SHA      commit precedente al push; se vuoto o 000..., deploy completo
#   AFTER_SHA       commit da deployare (default HEAD)
#   DRY_RUN=1       stampa le operazioni senza chiamare l'API
set -euo pipefail

: "${PA_USERNAME:?PA_USERNAME mancante}"
: "${PA_PROJECT_DIR:?PA_PROJECT_DIR mancante}"
if [[ "${DRY_RUN:-0}" != "1" ]]; then
  : "${PA_API_TOKEN:?PA_API_TOKEN mancante}"
fi

PA_HOST="${PA_HOST:-www.pythonanywhere.com}"
# Il dominio della web app è sempre in minuscolo, anche se lo username ha maiuscole
PA_DOMAIN="${PA_DOMAIN:-$(printf '%s' "$PA_USERNAME" | tr '[:upper:]' '[:lower:]').pythonanywhere.com}"
PA_PROJECT_DIR="${PA_PROJECT_DIR%/}"
AFTER_SHA="${AFTER_SHA:-HEAD}"
API="https://${PA_HOST}/api/v0/user/${PA_USERNAME}"

# Solo queste cartelle vengono pubblicate sul server
DEPLOY_PATHS=(backend frontend)

api() {
  # api METHOD URL [argomenti curl extra...]
  local method="$1" url="$2"; shift 2
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    echo "[dry-run] $method $url $*"
    return 0
  fi
  local status
  status=$(curl -sS -o /tmp/pa_response -w '%{http_code}' -X "$method" \
    -H "Authorization: Token ${PA_API_TOKEN}" "$@" "$url")
  echo "$status"
}

upload() {
  local file="$1" status
  status=$(api POST "${API}/files/path${PA_PROJECT_DIR}/${file}" -F "content=@${file}")
  case "$status" in
    200|201|"[dry-run]"*) echo "↑ ${file}" ;;
    *) echo "::error::Upload di ${file} fallito (HTTP ${status}): $(cat /tmp/pa_response 2>/dev/null)"; exit 1 ;;
  esac
}

remove() {
  local file="$1" status
  status=$(api DELETE "${API}/files/path${PA_PROJECT_DIR}/${file}")
  case "$status" in
    200|204|404|"[dry-run]"*) echo "✕ ${file}" ;;
    *) echo "::error::Eliminazione di ${file} fallita (HTTP ${status}): $(cat /tmp/pa_response 2>/dev/null)"; exit 1 ;;
  esac
}

uploads=()
deletes=()

# Se sul server manca il codice (web app nuova), il deploy è completo anche dopo un push
server_empty=0
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  [[ "${SIMULATE_EMPTY_SERVER:-0}" == "1" ]] && server_empty=1
else
  marker_status=$(api GET "${API}/files/path${PA_PROJECT_DIR}/backend/app.py")
  case "$marker_status" in
    200) ;;
    404) server_empty=1; echo "Sul server non c'è ancora il codice: primo deploy." ;;
    *) echo "::error::Controllo del server fallito (HTTP ${marker_status}): $(cat /tmp/pa_response 2>/dev/null)"; exit 1 ;;
  esac
fi

if (( server_empty )) || [[ -z "${BEFORE_SHA:-}" || "${BEFORE_SHA}" =~ ^0+$ ]] || ! git cat-file -e "${BEFORE_SHA}^{commit}" 2>/dev/null; then
  echo "Deploy completo di: ${DEPLOY_PATHS[*]}"
  while IFS= read -r f; do uploads+=("$f"); done < <(git ls-files -- "${DEPLOY_PATHS[@]}")
else
  echo "Deploy incrementale ${BEFORE_SHA:0:7}..${AFTER_SHA:0:7}"
  while IFS=$'\t' read -r status f; do
    case "$status" in
      D) deletes+=("$f") ;;
      *) uploads+=("$f") ;;
    esac
  done < <(git diff --no-renames --name-status "${BEFORE_SHA}" "${AFTER_SHA}" -- "${DEPLOY_PATHS[@]}")
fi

if (( ${#uploads[@]} == 0 && ${#deletes[@]} == 0 )); then
  echo "Nessun file da pubblicare."
  exit 0
fi

for f in "${uploads[@]+"${uploads[@]}"}"; do upload "$f"; done
for f in "${deletes[@]+"${deletes[@]}"}"; do remove "$f"; done

status=$(api POST "${API}/webapps/${PA_DOMAIN}/reload/")
case "$status" in
  200|"[dry-run]"*) echo "↻ Web app ${PA_DOMAIN} ricaricata" ;;
  *) echo "::error::Reload fallito (HTTP ${status}): $(cat /tmp/pa_response 2>/dev/null)"; exit 1 ;;
esac
