import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask_sqlalchemy import SQLAlchemy

#   vvv
#   vvvvv
#
#   Setup logistics and DB connection functions borrowed from Flaskr documentation
# 
#   ^^^^^
#   ^^^



app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/ethandjay/Documents/College/sophomore/330/fall2016-cp-ethan-jaynes-443837/NewDB.db'


# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'app.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLICKR_SETTINGS', silent=True)

def connect_db():
    #Connects to database
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    #Opens a new database connection if there is none yet for the current application context.
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    #Closes the database again at the end of the request.
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
        
def init_db():
    db = get_db()
    with app.open_resource('db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    #Initializes the database.
    init_db()
    print 'Initialized the database.'


####    ROUTING


# @app.route("/")
# def main():
#     return "Welcome!"

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('show_entries'))

@app.route('/show_entries')
def show_entries():
    db = get_db()
    cur = db.execute('select imgpath, title, description from pictures')
    pictures = cur.fetchall()
    return render_template('show_entries.html', pictures=pictures)

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('insert into pictures (title, description) values (?, ?)',
        [request.form['title'], request.form['description']])
    db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select username, password from users')
        users = cur.fetchall()
        for user in users:
            if request.form['username'] == user.username and request.form['password'] == user.password:
                session['username'] = request.form['username']
                return redirect(url_for('show_entries'))
        return render_template('login.html', error="Incorrect username or password")
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    error = None
    if request.method == 'POST':
        db = get_db()
        cur = db.execute('select username from users')
        users = cur.fetchall()
        for user in users:
            if request.form['username'] == user.username:
                return render_template('login.html', error="Username Taken")
        session['username'] = request.form['username']
        db.execute('insert into users (username, password) values (?, ?)', [request.form['username'], request.form['password']])
        db.commit()
        
        db = get_db()
        cur = db.execute('select imgpath from pictures')
        pictures = cur.fetchall()
        return render_template('show_entries.html', pictures=pictures)
        # if request.form['username'] != app.config['USERNAME']:
        #     error = 'Invalid username'
        # elif request.form['password'] != app.config['PASSWORD']:
        #     error = 'Invalid password'
        # else:
        #     session['logged_in'] = True
        #     flash('You were logged in')
        #     return redirect(url_for('show_entries'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You were logged out')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run()