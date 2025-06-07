from flask import Flask, render_template, redirect, request, session, flash
import sqlite3
import uuid
from datetime import timedelta
from functools import wraps  # Aggiunto per il decorator

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = b'ciao1234'
app.permanent_session_lifetime = timedelta(minutes=30)



def init_db():
    """Funzione per creare le tabelle solo se non esistono già."""
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            pass TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            todo TEXT,
            info TEXT,
            shared TEXT,
            done BOOLEAN,
            user_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    connection.commit()
    connection.close()

def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection


init_db()

def check_password(stored_password, provided_password):
    return stored_password == provided_password


def login_required(f):
    @wraps(f)  # Mantiene il nome della funzione originale
    def wrapper(*args, **kwargs):
        if 'id' not in session:
            flash('Please login to access this page.', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
@login_required
def home():
    connection = get_db_connection()
    todos = connection.execute('SELECT * FROM todos WHERE user_id= ? AND done=0', (session['id'],)).fetchall()
    connection.close()
    todos = list(todos)
    todos.reverse()
    return render_template('home.html', todos=todos, username=session['username'])

@app.route('/done')
@login_required
def done():
    connection = get_db_connection()
    todos = connection.execute('SELECT * FROM todos WHERE user_id= ? AND done=1', (session['id'],)).fetchall()
    connection.close()
    todos = list(todos)
    todos.reverse()
    return render_template('done.html', todos=todos, username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        existingUser = connection.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existingUser is not None:
            flash('Questo username è già in uso. Scegli un altro username.', 'error')
        else:
            userId = str(uuid.uuid4())
            connection.execute('INSERT INTO users (id, username, pass) VALUES (?, ?, ?)',
                               (userId, username, password))
            connection.commit()
            flash('Ti sei registrato con successo!', 'success')
            session.permanent = True
            session["id"] = userId
            session['username'] = username
            return redirect('/home')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        user = connection.execute('SELECT id, username, pass FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password(user['pass'], password):
            session.permanent = True
            session['id'] = user['id']
            session['username'] = user['username']
            flash('Login effettuato con successo!', 'success')
            return redirect('/home')
        else:
            flash('Username o password errati. Riprova.', 'error')
        connection.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout effettuato con successo', 'success')
    return redirect('/')

@app.route('/<int:index>/delete', methods=('POST',))
@login_required
def delete(index):
    connection = get_db_connection()
    connection.execute('DELETE FROM todos WHERE id=?', (index,))
    connection.commit()
    connection.close()
    flash('Todo eliminato con successo', 'success')
    return redirect('/home')

@app.route('/<int:index>/modify', methods=('POST','GET'))
@login_required
def modify(index):
    connection = get_db_connection()
    oldTodo = connection.execute('SELECT * FROM todos WHERE id=?', (index,)).fetchone()
    if request.method == 'POST':
        newTodo = request.form['todo']
        newInfo = request.form['info']
        if newInfo == oldTodo['info'] and newTodo == oldTodo['todo']:
            flash('Nessuna modifica apportata', 'info')
            return redirect('/home')
        connection.execute('UPDATE todos SET todo=?, info=? WHERE id=?', (newTodo, newInfo, index))
        connection.commit()
        connection.close()
        flash('Todo modificato correttamente', 'success')
        return redirect('/home')
    return render_template('modify.html', todo=oldTodo, username=session['username'])

@app.route('/<int:index>/share', methods=('POST','GET'))
@login_required
def share(index):
    connection = get_db_connection()
    if request.method == 'POST':
        username = request.form['username']
        todoRow = connection.execute('SELECT * FROM todos WHERE id=?', (index,)).fetchone()
        todo = todoRow['todo']
        info = todoRow['info']
        done = todoRow['done']
        user = connection.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if user:
            userId = user['id']
            connection.execute('INSERT INTO todos (todo,info,user_id,shared,done) VALUES (?,?,?,?,?)',
                               (todo, info, userId, session['username'],done))
            connection.commit()
            flash('Todo condiviso con successo', 'success')
        else:
            flash('Utente non trovato', 'error')
        connection.close()
        return redirect('/home')
    return render_template('share.html', username=session['username'])

@app.route('/insert', methods=('GET', 'POST'))
@login_required
def insert():
    if request.method == 'POST':
        todo = request.form['todo']
        info = request.form['info']
        connection = get_db_connection()
        connection.execute(
            'INSERT INTO todos (todo,info,user_id,done) VALUES (?,?,?,?)',
            (todo, info, session['id'], False)
        )
        connection.commit()
        connection.close()
        flash('Todo aggiunto con successo', 'success')
        return redirect('/home')
    return render_template('insert.html', username=session['username'])

@app.route('/<int:index>/update_status', methods=['POST'])
@login_required
def update_status(index):
    connection = get_db_connection()
    completed = 'completed' in request.form
    connection.execute('UPDATE todos SET done=? WHERE id=?', (completed, index))
    connection.commit()
    connection.close()
    if request.referrer == 'http://127.0.0.1:5000/done':
        return redirect('/done')
    return redirect('/home')

if __name__ == "__main__":
    app.run(debug=True)
