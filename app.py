import sqlite3
import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = '/Users/ethandjay/Documents/College/sophomore/330/fall2016-cp-ethan-jaynes-443837/static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/ethandjay/Documents/College/sophomore/330/fall2016-cp-ethan-jaynes-443837/NewDB.db'
db = SQLAlchemy(app)
db.drop_all()
db.create_all()

# Load default config and override config from an environment variable
app.config.update(dict(
    SECRET_KEY = 'suh',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLICKR_SETTINGS', silent=True)

#Some structuring for followers/following relationships borrowed from https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-viii-followers-contacts-and-friends, as per TA suggestion



    
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)
blockers = db.Table('blockers',
    db.Column('blocker_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('blocked_id', db.Integer, db.ForeignKey('user.id'))
)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)
    profpicpath = db.Column(db.Text, unique = True)
    followed = db.relationship('User', 
                               secondary=followers, 
                               primaryjoin=(followers.c.follower_id == id), 
                               secondaryjoin=(followers.c.followed_id == id), 
                               backref=db.backref('followers', lazy='dynamic'), 
                               lazy='dynamic')
    blocked = db.relationship('User', 
                               secondary=blockers, 
                               primaryjoin=(blockers.c.blocker_id == id), 
                               secondaryjoin=(blockers.c.blocked_id == id), 
                               backref=db.backref('blockers', lazy='dynamic'), 
                               lazy='dynamic')

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return '<User %r>' % self.username
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0
    
    def block(self, user):
        if not self.is_blocking(user):
            self.blocked.append(user)
            return self

    def unblock(self, user):
        if self.is_blocking(user):
            self.blocked.remove(user)
            return self

    def is_blocking(self, user):
        return self.blocked.filter(blockers.c.blocked_id == user.id).count() > 0

class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    imgpath = db.Column(db.Text, unique=True)
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    owner = db.Column(db.Text, db.ForeignKey('user.id'))

    def __init__(self, imgpath, title, description, owner):
        self.imgpath = imgpath
        self.title = title
        self.description = description
        self.owner = owner

    def __repr__(self):
        return '<Picture %r>' % self.id

    
####    ROUTING

#  vvvvvvvvv

#   Significant stylistic choices and functionality for routing borrowed from Flask documentation examples/tutorial

#  ^^^^^^^^^

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('show_entries'))
    
# Main page

@app.route('/show_entries')
def show_entries():
    user = User.query.filter_by(username=session['username']).first()
    pictures = Picture.query.all()
    pictures = [picture for picture in pictures if (user.is_following(User.query.filter_by(username=picture.owner).first()) or user.username == User.query.filter_by(username=picture.owner).first().username) and not user.is_blocking(User.query.filter_by(username=picture.owner).first())]
    pictures.sort(key=lambda x: x.id, reverse=True)
    return render_template('show_entries.html', pictures=pictures, afterupload=False)

# Login logic

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        users = User.query.all()
        for user in users:
            if request.form['username'] == user.username and request.form['password'] == user.password:
                session['username'] = request.form['username']
                return redirect(url_for('show_entries'))
        return render_template('login.html', error="Incorrect username or password")
    return render_template('login.html')

# Register logic

@app.route('/register', methods=['POST'])
def register():
    error = None
    if request.method == 'POST':
        users = User.query.all()
        for user in users:
            if request.form['username'] == user.username:
                return render_template('login.html', error="Username Taken")
        session['username'] = request.form['username']
        db.session.add(User(request.form['username'], request.form['password']))
        db.session.commit()
        
        return redirect(url_for('show_entries'))
    
    #Check if legal file

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
        
# Image upload logic

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    user = User.query.filter_by(username=session['username']).first()
    pictures = Picture.query.all()
    for picture in pictures:
        other = User.query.filter_by(username=picture.owner).first()
        if not user.is_following(other):
            pictures.remove(picture)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            db.session.add(Picture(filename, request.form['title'], request.form['description'], session['username']))
            db.session.commit()
            # if request.form['from_userpage'] == "True":
            #     return redirect(url_for('userpage', user=request.form['user']))
            # else:
            return render_template('show_entries.html', afterupload=True, pictures=pictures)
    flash("Something didn't work.")
    return render_template('show_entries.html', afterupload=True, pictures=pictures)

# All user page logic

@app.route('/allusers')
def allusergen():
    users = User.query.all()
    return render_template('allusers.html', users=users)

# User page logic

@app.route('/userpage')
def userpage():
    numFollowers = 0
    numFollowing = 0
    numBlocked = 0
    me = User.query.filter_by(username=session['username']).first()
    users = User.query.all()
    you = request.args['user']
    you = User.query.filter_by(username=you).first()
    pictureList = Picture.query.all()
    pictureList.sort(key=lambda x: x.id, reverse=True)
    pictures = []
    if me.is_blocking(you):
        urblocked = True
    else:
        urblocked = False
    if you.is_blocking(me):
        imblocked = True
    else:
        imblocked = False
    for picture in pictureList:
        if picture.owner==you.username:
            pictures.append(picture)
    for user in users:
        if you.is_following(user):
            numFollowing += 1
        if user.is_following(you):
            numFollowers += 1
        if you.is_blocking(user):
            numBlocked += 1
    if me.is_following(you):
        fwg = True
    else:
        fwg = False
    return render_template('userpage.html', me=me, users=users, user=you, fwg=fwg, pictures=pictures, numFrs=numFollowers, numFng=numFollowing, numBlk = numBlocked, urblocked=urblocked, imblocked=imblocked)

# Follow or unfollow user

@app.route('/followdo', methods=['POST'])
def followdo():
    me = User.query.filter_by(username=session['username']).first()
    you = User.query.filter_by(username=request.form['you']).first()
    if request.form['action'] == "Follow":
        f = me.follow(you)
        db.session.add(f)
        db.session.commit()
    else:
        f = me.unfollow(you)
        db.session.add(f)
        db.session.commit()
    if 'from_list' in request.form:
        return redirect(url_for('show_entries'))
    return redirect(url_for('userpage', user=you.username))

# Block or unblock user

@app.route('/blockdo', methods=['POST'])
def blockdo():
    me = User.query.filter_by(username=session['username']).first()
    you = User.query.filter_by(username=request.form['you']).first()
    if request.form['action'] == "Block":
        f = me.block(you)
        if you.is_following(me):
            g = you.unfollow(me)
            db.session.add(g)
        if me.is_following(you):
            h = me.unfollow(you)
            db.session.add(h)
        db.session.add(f)
        db.session.commit()
        flash(request.form['you'] + " successfully blocked")
        return redirect(url_for('show_entries'))
        
    else:
        f = me.unblock(you)
        db.session.add(f)
        db.session.commit()
        flash(request.form['you'] + " successfully unblocked")
        return redirect(url_for('userpage', user=you.username))

# Get follower list logic

@app.route('/followersList', methods=['GET'])
def followersListGen():
    you = User.query.filter_by(username=request.args['user']).first()
    users = User.query.all()
    followersList = []
    followersListRecip = {}
    for user in users:
        if user.is_following(you):
            followersList.append(user)
        if you.is_following(user):
            followersListRecip[user.username] = True
        else:
            followersListRecip[user.username] = False
    return render_template('followersList.html', followersList=followersList, followersListRecip=followersListRecip, currentUser=request.args['user'])
     
     # Get following list logic   
    
@app.route('/followingList', methods=['GET'])
def followingListGen():
    you = User.query.filter_by(username=request.args['user']).first()
    users = User.query.all()
    followingList = []
    for user in users:
        if you.is_following(user):
            followingList.append(user)
    return render_template('followingList.html', followingList=followingList, currentUser=request.args['user'])

# Get block list logic

@app.route('/blockedList', methods=['GET'])
def blockedListGen():
    you = User.query.filter_by(username=request.args['user']).first()
    users = User.query.all()
    blockedList = []
    for user in users:
        if you.is_blocking(user):
            blockedList.append(user)
    return render_template('blockedList.html', blockedList=blockedList, currentUser=request.args['user'])

# Logout

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You were logged out')
    return redirect(url_for('home'))

# Image page logic

@app.route('/imagepage')
def imagepagegen():
    picture = Picture.query.filter_by(id=request.args['id']).first()
    return render_template('imagepage.html', picture=picture)

# Edit image data page redir

@app.route('/edit')
def editpic():
    picture = Picture.query.filter_by(id=request.args['id']).first()
    return render_template("edit.html", picture=picture)

# Edit image data logic

@app.route('/doedit', methods=['POST'])
def doedit():
    pic = Picture.query.filter_by(id=request.form['id']).first()
    path = pic.imgpath
    owner = pic.owner
    db.session.delete(pic)
    db.session.commit()
    newpic = Picture(path, request.form['title'], request.form['description'], owner)
    db.session.add(newpic)
    db.session.commit()
    return render_template("imagepage.html", picture=newpic)

# Delete image

@app.route('/delete', methods=['GET'])
def delete():
    pic = Picture.query.filter_by(id=request.args['id']).first()
    db.session.delete(pic)
    db.session.commit()
    flash("Image successfully deleted")
    return redirect(url_for('show_entries'))

# Upload profile picture

@app.route('/uploadprof', methods=['GET', 'POST'])
def uploadprof():
    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profpicpath = filename
            db.session.commit()
            # if request.form['from_userpage'] == "True":
            #     return redirect(url_for('userpage', user=request.form['user']))
            # else:
            return redirect(url_for('userpage', user=session['username']))
    flash("Something didn't work.")
    return redirect(url_for('userpage', user=session['username']))


if __name__ == "__main__":
    app.run()