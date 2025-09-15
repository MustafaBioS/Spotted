from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, login_user, logout_user, LoginManager, current_user, login_required
from sqlalchemy import exc
from sqlalchemy.orm import joinedload
import os
from PIL import Image
import io

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
    password = db.Column(db.Text, nullable=False)
    pfp = db.Column(db.String(200), default='/static/uploads/default.png')
    is_artist = db.Column(db.Boolean, default=False)

class Songs(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    songname = db.Column(db.String(64), nullable=False) 
    audiofile = db.Column(db.String(120), nullable=False)
    genre = db.Column(db.String(64), nullable=False)

    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, name="fk_songs_users")
    artist = db.relationship('Users', backref='songs')

playlist_songs = db.Table(
    'playlist_songs',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id'), primary_key=True),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.id'), primary_key=True)
)

class Playlists(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlistname = db.Column(db.String(64), nullable=False)
    playlistpic = db.Column(db.String(200), default='/static/playlistpics/defaultpl.png')

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('Users', backref='playlists')
    
    songs = db.relationship('Songs', secondary=playlist_songs, backref='playlists')


# ROUTES

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route('/home')
@login_required
def home():
    playlists = Playlists.query.filter_by(user_id=current_user.id).all()
    songs = Songs.query.all()
    return render_template('index.html', songs=songs, playlists=playlists)

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
@login_required
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
    playlists = Playlists.query.filter_by(user_id=current_user.id).all()
    songs = Songs.query.options(joinedload(Songs.artist)).filter_by(genre=genre).all()
    return render_template('genre.html', genre=genre,   songs=songs, playlists=playlists)


@app.route('/settings/<int:user_id>', methods=['GET', 'POST'])
@login_required
def settings(user_id):
    user_id = current_user.id

    if request.method == 'GET':
        return render_template('settings.html', user_id=user_id)
    if request.method == 'POST':
        user = Users.query.filter_by(username=current_user.username).first()

        newusername = request.form.get('newuser')
        userpass = request.form.get('passverify')

        newpfp = request.files.get('newpfp')

        newpass = request.form.get('newpass')
        oldpass = request.form.get('oldpass')

        if newusername and userpass:
            if bcrypt.check_password_hash(user.password, userpass):
                user.username = newusername
                db.session.commit()
                flash('Username Updated Successfully', 'success')
            else:
                flash('Incorrect Password', 'fail')

            return redirect(url_for('settings', user_id=user_id))
        
        if newpfp:
            if newpfp.filename != '':
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)

                filename = newpfp.filename  
                filepath = os.path.join(upload_folder, filename)

                img = Image.open(newpfp)
                max_width, max_height = 512, 512

                if img.width > max_width or img.height > max_height:
                    flash(f'Image Is Too Large, Max Size Is 512 x 512', 'fail')
                    return redirect(url_for('settings', user_id=user_id))
                
                newpfp.stream.seek(0)
                newpfp.save(filepath)

                user.pfp = f"/static/uploads/{filename}"
                db.session.commit()
                flash('Profile Picture Updated Successfully', 'success')

            else:
                flash('No file selected', 'fail')

            return redirect(url_for('settings', user_id=user_id))
        
        if newpass and oldpass:
            if bcrypt.check_password_hash(user.password, oldpass):
                user.password = bcrypt.generate_password_hash(newpass).decode('utf-8')
                db.session.commit()
                flash('Password Updated Successfully', 'success')
            else:
                flash('Incorrect Password', 'fail')

            return redirect(url_for('settings', user_id=user_id))        

@app.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete(user_id):

    if request.method == 'POST':
        deletepass = request.form.get('deletepass')
        confirmpass = request.form.get('confirmpass')

        if user_id != current_user.id:
            flash("Nice Try Buddy...", 'fail')
            return redirect(url_for('settings', user_id=user_id))
        
        if deletepass != confirmpass:
            flash('Passwords Do Not Match', 'fail')
            return redirect(url_for('settings', user_id=user_id))

        user = Users.query.filter_by(id=current_user.id).first()
        if bcrypt.check_password_hash(user.password, deletepass):

            db.session.delete(user)
            db.session.commit()
            logout_user()
            flash('Account Deleted Successfully', 'success')
            return redirect(url_for('signup'))
        else:
            flash('Incorrect Password', 'fail')
            return redirect(url_for('settings', user_id=user_id))

@app.route('/createplaylist', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'GET':
        playlists = Playlists.query.filter_by(user_id=current_user.id).all()
        return render_template('create.html', playlists=playlists)
    if request.method == 'POST':
        plname = request.form.get('plname')
        plpfp = request.files.get('newpfp')

        plpic_path = "/static/playlistpics/defaultpl.png"
        if plpfp and plpfp.filename != '':
            upload_folder = os.path.join('static', 'playlistpics')
            os.makedirs(upload_folder, exist_ok=True)

            filename = plpfp.filename
            filepath = os.path.join(upload_folder, filename)
            plpfp.save(filepath)
    
            plpic_path = f"/static/playlistpics/{filename}"

        playlist = Playlists(playlistname=plname, playlistpic=plpic_path, user_id=current_user.id)

        db.session.add(playlist)
        db.session.commit()
        flash('Playlist Created Successfully', 'success')
        return redirect(url_for('home'))

@app.route('/Playlist/<int:playlist_id>')
@login_required
def playlist(playlist_id):
    playlists = Playlists.query.filter_by(user_id=current_user.id).all()
    playlist = Playlists.query.get_or_404(playlist_id)
    return render_template('pl.html', playlist=playlist, songs=playlist.songs, playlists=playlists)

@app.route('/playlist/<int:playlist_id>/add/<int:song_id>')
def add(playlist_id, song_id):
    playlist = Playlists.query.get_or_404(playlist_id)
    song = Songs.query.get_or_404(song_id)

    if song not in playlist.songs:
        playlist.songs.append(song)
        db.session.commit()
        flash('Song Added To Playlist Successfully', 'success')
        return redirect(url_for('playlist', playlist_id=playlist.id))
    else:
        flash('Song Already In Playlist', 'fail')
        return redirect(url_for('playlist', playlist_id=playlist.id))

# RUN

if __name__ == '__main__':
    app.run(debug=True)