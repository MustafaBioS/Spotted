from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, login_user, logout_user, LoginManager, current_user, login_required
from sqlalchemy import exc
from sqlalchemy.orm import joinedload
import os

# APP INITIALIZATION

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config['SECRET_KEY'] = 'SpottedDupeFlaskProjectSiege'

db = SQLAlchemy(app)

migrate = Migrate(app, db)

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MODELS

class Users(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    password = db.Column(db.String(64), nullable=False)
    pfp = db.Column(db.String(200), default='static/uploads/default.png')
    is_artist = db.Column(db.Boolean, default=False)

class Songs(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    songname = db.Column(db.String(64), nullable=False) 
    audiofile = db.Column(db.String(120), nullable=False)
    genre = db.Column(db.String(64), nullable=False)

    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, name="fk_songs_users")
    artist = db.relationship('Users', backref='songs')


# ROUTES

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route('/home')
@login_required
def home():
    songs = Songs.query.all()
    return render_template('index.html', songs=songs)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        checkbox = bool(request.form.get('checkbox'))

        try:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            new_user = Users(username=username, password=hashed_pw, is_artist=checkbox)

            db.session.add(new_user)
            db.session.commit()
            flash('Signup Successfull, Please Login.', 'success')
            return redirect(url_for('login'))

        except exc.SQLAlchemyError:
            flash('Username Is Already Taken', 'fail')
            return redirect(url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Users.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Successfully Logged In', 'success')
            return redirect(url_for('home'))
        else:
            flash('Incorrect Credentials')
            return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You Have Been Logged Out', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
    if request.method == 'POST':
        songname = request.form.get('songname')
        genre = request.form.get('genre')
        file = request.files['audiofile']
        if file and file.filename.endswith('.mp3'):
            filename = file.filename
            filepath = os.path.join('static/songuploads', filename)
            file.save(filepath)

            song = Songs(songname=songname, 
                         artist_id=current_user.id, 
                         audiofile= f"/static/songuploads/{filename}", 
                         genre=genre
                         )

            db.session.add(song)
            db.session.commit()
            return redirect(url_for('home'))

@app.route('/genre/<genre>')
@login_required
def genre(genre):
    songs = Songs.query.options(joinedload(Songs.artist)).filter_by(genre=genre).all()
    return render_template('playlist.html', genre=genre, songs=songs)


@app.route('/settings/<int:user_id>', methods=['GET', 'POST'])
@login_required
def settings(user_id):
    user_id = current_user.id
    if request.method == 'GET':
        return render_template('settings.html', user_id=user_id)


# RUN

if __name__ == '__main__':
    app.run(debug=True)