// TodoApp — interazioni fluide (progressive enhancement: senza JS i form funzionano comunque)
(() => {
  window.TodoApp = true;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, reduceMotion ? 0 : ms));

  /* ---------- Toast ---------- */

  const toastRoot = document.querySelector('.toasts');

  function dismissToast(el) {
    if (el.classList.contains('is-leaving')) return;
    el.classList.add('is-leaving');
    el.addEventListener('animationend', () => el.remove(), { once: true });
    setTimeout(() => el.remove(), 600);
  }

  function armToast(el, delay) {
    el.addEventListener('click', () => dismissToast(el));
    setTimeout(() => dismissToast(el), delay);
  }

  function toast(message, kind = 'success') {
    if (!toastRoot) return;
    const el = document.createElement('div');
    el.className = `toast toast-${kind}`;
    const tpl = document.getElementById(`toast-${kind}`);
    if (tpl) el.appendChild(tpl.content.cloneNode(true));
    const text = document.createElement('span');
    text.textContent = message;
    el.appendChild(text);
    toastRoot.appendChild(el);
    armToast(el, 2800);
  }

  document.querySelectorAll('.toast').forEach((el, i) => armToast(el, 3200 + i * 400));

  /* ---------- Richieste in background ---------- */

  async function post(form, body) {
    const res = await fetch(form.action, { method: 'POST', body, credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    // Sessione scaduta: il backend reindirizza alla landing
    if (new URL(res.url).pathname === '/') {
      window.location.href = '/';
      throw new Error('session-expired');
    }
  }

  async function collapse(row) {
    row.style.height = `${row.offsetHeight}px`;
    void row.offsetHeight; // forza il reflow
    row.classList.add('is-collapsing');
    row.style.height = '0px';
    await wait(340);
    row.remove();
    refreshCount();
  }

  function refreshCount() {
    const list = document.querySelector('.todo-list');
    const n = list ? list.querySelectorAll('.todo-row').length : 0;
    const counter = document.querySelector('[data-count]');
    if (counter) counter.textContent = `${n} ${n === 1 ? counter.dataset.one : counter.dataset.many}`;
    if (n === 0) {
      list?.closest('.group')?.remove();
      document.querySelector('.empty')?.removeAttribute('hidden');
    }
  }

  /* ---------- Completa / ripristina ---------- */

  document.addEventListener('change', async (e) => {
    const input = e.target.closest('.check-form input[type="checkbox"]');
    if (!input) return;
    const form = input.form;
    const row = input.closest('.todo-row');
    const body = new FormData(form);

    row.classList.toggle('is-done', input.checked);
    const check = input.closest('.check');
    check.classList.remove('pop');
    void check.offsetWidth;
    check.classList.add('pop');

    try {
      await Promise.all([post(form, body), wait(520)]);
      await collapse(row);
    } catch (err) {
      if (err.message !== 'session-expired') form.submit();
    }
  });

  /* ---------- Elimina ---------- */

  document.addEventListener('submit', async (e) => {
    const form = e.target.closest('.delete-form');
    if (!form) return;
    e.preventDefault();
    const row = form.closest('.todo-row');
    try {
      await Promise.all([post(form, new FormData(form)), collapse(row)]);
      toast('Promemoria eliminato');
    } catch (err) {
      if (err.message !== 'session-expired') window.location.reload();
    }
  });

  /* ---------- Controllo segmentato: fa scorrere il selettore prima di navigare ---------- */

  document.querySelectorAll('.segmented a').forEach((link) => {
    link.addEventListener('click', (e) => {
      if (link.classList.contains('is-active') || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      const seg = link.closest('.segmented');
      seg.dataset.active = link.dataset.key;
      seg.querySelectorAll('a').forEach((a) => a.classList.toggle('is-active', a === link));
      setTimeout(() => { window.location.href = link.href; }, reduceMotion ? 0 : 230);
    });
  });

  /* ---------- Link "indietro" ---------- */

  document.querySelectorAll('[data-back]').forEach((link) => {
    link.addEventListener('click', (e) => {
      if (document.referrer && new URL(document.referrer).origin === window.location.origin) {
        e.preventDefault();
        history.back();
      }
    });
  });

  /* ---------- Textarea che cresce col contenuto ---------- */

  document.querySelectorAll('.field textarea').forEach((ta) => {
    const fit = () => {
      ta.style.height = 'auto';
      ta.style.height = `${ta.scrollHeight}px`;
    };
    ta.addEventListener('input', fit);
    fit();
  });

  /* ---------- Cursore a fine testo nei campi precompilati ---------- */

  const auto = document.querySelector('.field input[autofocus]');
  if (auto && auto.value) {
    const len = auto.value.length;
    try { auto.setSelectionRange(len, len); } catch (_) { /* tipi senza selezione */ }
  }
})();
