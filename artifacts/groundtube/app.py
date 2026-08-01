import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_VIDEO = {'mp4', 'webm'}
ALLOWED_AUDIO = {'mp3', 'wav'}
ALLOWED_THUMB = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'groundtube-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'groundtube.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

CATEGORIES = [
    'Gaming', 'Music', 'Sports', 'Education', 'Technology',
    'Entertainment', 'News', 'Travel', 'Food', 'Fashion',
    'Comedy', 'Art', 'Science', 'Automotive', 'Other'
]

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default='user')  # 'user' or 'admin'
    bio = db.Column(db.Text, default='')
    avatar = db.Column(db.String(256), default='')
    banner = db.Column(db.String(256), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_suspended = db.Column(db.Boolean, default=False)

    videos = db.relationship('Video', backref='author', lazy='dynamic',
                              foreign_keys='Video.user_id')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    likes = db.relationship('Like', backref='user', lazy='dynamic')
    reports = db.relationship('Report', backref='reporter', lazy='dynamic',
                               foreign_keys='Report.reporter_id')

    @property
    def subscriber_count(self):
        return Subscription.query.filter_by(channel_id=self.id).count()

    @property
    def video_count(self):
        return Video.query.filter_by(user_id=self.id, is_deleted=False).count()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def avatar_url(self):
        if self.avatar:
            return url_for('static', filename='uploads/avatars/' + self.avatar)
        return url_for('static', filename='img/default_avatar.png')


class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    filename = db.Column(db.String(256), nullable=False)
    thumbnail = db.Column(db.String(256), default='')
    media_type = db.Column(db.String(8), default='video')  # 'video' or 'audio'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(64), default='Other')
    tags = db.Column(db.String(500), default='')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    comments = db.relationship('Comment', backref='video', lazy='dynamic',
                                cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='video', lazy='dynamic',
                              cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='video', lazy='dynamic',
                               foreign_keys='Report.video_id',
                               cascade='all, delete-orphan')

    @property
    def like_count(self):
        return Like.query.filter_by(video_id=self.id, type='like').count()

    @property
    def dislike_count(self):
        return Like.query.filter_by(video_id=self.id, type='dislike').count()

    @property
    def comment_count(self):
        return Comment.query.filter_by(video_id=self.id, is_deleted=False).count()

    def thumbnail_url(self):
        if self.thumbnail:
            return url_for('static', filename='uploads/thumbnails/' + self.thumbnail)
        if self.media_type == 'audio':
            return url_for('static', filename='img/audio_thumb.png')
        return url_for('static', filename='img/video_thumb.png')

    def file_url(self):
        folder = 'videos' if self.media_type == 'video' else 'audio'
        return url_for('static', filename=f'uploads/{folder}/{self.filename}')

    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days >= 365:
            n = delta.days // 365
            return f'{n} year{"s" if n > 1 else ""} ago'
        if delta.days >= 30:
            n = delta.days // 30
            return f'{n} month{"s" if n > 1 else ""} ago'
        if delta.days >= 1:
            return f'{delta.days} day{"s" if delta.days > 1 else ""} ago'
        hours = delta.seconds // 3600
        if hours >= 1:
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        mins = delta.seconds // 60
        if mins >= 1:
            return f'{mins} minute{"s" if mins > 1 else ""} ago'
        return 'Just now'

    def format_views(self):
        v = self.views
        if v >= 1_000_000:
            return f'{v/1_000_000:.1f}M'
        if v >= 1_000:
            return f'{v/1_000:.1f}K'
        return str(v)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side='Comment.id'),
                               lazy='dynamic')

    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        if delta.days >= 365:
            n = delta.days // 365
            return f'{n} year{"s" if n > 1 else ""} ago'
        if delta.days >= 30:
            n = delta.days // 30
            return f'{n} month{"s" if n > 1 else ""} ago'
        if delta.days >= 1:
            return f'{delta.days} day{"s" if delta.days > 1 else ""} ago'
        hours = delta.seconds // 3600
        if hours >= 1:
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        mins = delta.seconds // 60
        if mins >= 1:
            return f'{mins} minute{"s" if mins > 1 else ""} ago'
        return 'Just now'


class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    type = db.Column(db.String(8), nullable=False)  # 'like' or 'dislike'
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='unique_user_video_like'),)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('subscriber_id', 'channel_id',
                                          name='unique_subscription'),)


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_type = db.Column(db.String(16), nullable=False)  # 'video' or 'comment'
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def save_file(file_obj, subfolder):
    os.makedirs(os.path.join(UPLOAD_FOLDER, subfolder), exist_ok=True)
    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, subfolder, fname)
    file_obj.save(path)
    return fname


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('auth/register.html')

        if len(username) < 3 or len(username) > 32:
            flash('Username must be 3-32 characters.', 'error')
            return render_template('auth/register.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register.html')

        role = 'admin' if username.lower() == 'admin' else 'user'
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'Welcome to GroundTube, {username}!', 'success')
        return redirect(url_for('index'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter(
            (User.username == login_val) | (User.email == login_val.lower())
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'error')
            return render_template('auth/login.html')

        if user.is_suspended:
            flash('Your account has been suspended. Contact an admin.', 'error')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Main Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_deleted=False)\
        .order_by(desc(Video.created_at))\
        .paginate(page=page, per_page=24, error_out=False)
    return render_template('index.html', videos=videos, title='Home',
                           categories=CATEGORIES)


@app.route('/trending')
def trending():
    week_ago = datetime.utcnow() - timedelta(days=7)
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter(
        Video.is_deleted == False,
        Video.created_at >= week_ago
    ).order_by(desc(Video.views)).paginate(page=page, per_page=24, error_out=False)
    return render_template('index.html', videos=videos, title='Trending',
                           categories=CATEGORIES, active_section='trending')


@app.route('/category/<cat>')
def category(cat):
    if cat not in CATEGORIES:
        abort(404)
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter_by(is_deleted=False, category=cat)\
        .order_by(desc(Video.created_at))\
        .paginate(page=page, per_page=24, error_out=False)
    return render_template('index.html', videos=videos, title=cat,
                           categories=CATEGORIES, active_cat=cat)


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    videos = None
    if q:
        search_term = f'%{q}%'
        videos = Video.query.filter(
            Video.is_deleted == False,
            (Video.title.ilike(search_term) |
             Video.description.ilike(search_term) |
             Video.tags.ilike(search_term))
        ).order_by(desc(Video.views)).paginate(page=page, per_page=24, error_out=False)
    return render_template('search.html', videos=videos, query=q,
                           categories=CATEGORIES)


@app.route('/subscriptions')
@login_required
def subscriptions():
    subs = Subscription.query.filter_by(subscriber_id=current_user.id).all()
    channel_ids = [s.channel_id for s in subs]
    page = request.args.get('page', 1, type=int)
    videos = Video.query.filter(
        Video.is_deleted == False,
        Video.user_id.in_(channel_ids)
    ).order_by(desc(Video.created_at)).paginate(page=page, per_page=24, error_out=False)
    return render_template('index.html', videos=videos, title='Subscriptions',
                           categories=CATEGORIES, active_section='subscriptions')


# ---------------------------------------------------------------------------
# Video Routes
# ---------------------------------------------------------------------------

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Other')
        tags = request.form.get('tags', '').strip()
        media_file = request.files.get('media_file')
        thumb_file = request.files.get('thumbnail')

        if not title:
            flash('Title is required.', 'error')
            return render_template('video/upload.html', categories=CATEGORIES)

        if not media_file or not media_file.filename:
            flash('Please select a video or audio file.', 'error')
            return render_template('video/upload.html', categories=CATEGORIES)

        is_video = allowed_file(media_file.filename, ALLOWED_VIDEO)
        is_audio = allowed_file(media_file.filename, ALLOWED_AUDIO)

        if not is_video and not is_audio:
            flash('Unsupported file type. Use MP4, WEBM, MP3, or WAV.', 'error')
            return render_template('video/upload.html', categories=CATEGORIES)

        media_type = 'video' if is_video else 'audio'
        subfolder = 'videos' if is_video else 'audio'
        fname = save_file(media_file, subfolder)

        thumb_fname = ''
        if thumb_file and thumb_file.filename and allowed_file(thumb_file.filename, ALLOWED_THUMB):
            thumb_fname = save_file(thumb_file, 'thumbnails')

        if category not in CATEGORIES:
            category = 'Other'

        video = Video(
            title=title,
            description=description,
            filename=fname,
            thumbnail=thumb_fname,
            media_type=media_type,
            user_id=current_user.id,
            category=category,
            tags=tags
        )
        db.session.add(video)
        db.session.commit()
        flash('Your content has been uploaded!', 'success')
        return redirect(url_for('watch', video_id=video.uuid))

    return render_template('video/upload.html', categories=CATEGORIES)


@app.route('/watch/<video_id>')
def watch(video_id):
    video = Video.query.filter_by(uuid=video_id, is_deleted=False).first_or_404()
    # Increment views
    video.views += 1
    db.session.commit()

    # User interaction state
    user_like = None
    is_subscribed = False
    if current_user.is_authenticated:
        like = Like.query.filter_by(user_id=current_user.id, video_id=video.id).first()
        user_like = like.type if like else None
        is_subscribed = Subscription.query.filter_by(
            subscriber_id=current_user.id, channel_id=video.user_id
        ).first() is not None

    # Comments (top-level only)
    comments = Comment.query.filter_by(
        video_id=video.id, parent_id=None, is_deleted=False
    ).order_by(desc(Comment.created_at)).all()

    # Related videos (same category)
    related = Video.query.filter(
        Video.is_deleted == False,
        Video.id != video.id,
        Video.category == video.category
    ).order_by(desc(Video.views)).limit(15).all()

    if len(related) < 8:
        extra = Video.query.filter(
            Video.is_deleted == False,
            Video.id != video.id,
            Video.id.notin_([v.id for v in related])
        ).order_by(desc(Video.created_at)).limit(15 - len(related)).all()
        related += extra

    return render_template('video/watch.html', video=video, comments=comments,
                           related=related, user_like=user_like,
                           is_subscribed=is_subscribed)


@app.route('/delete_video/<video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.filter_by(uuid=video_id).first_or_404()
    if video.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    video.is_deleted = True
    db.session.commit()
    flash('Video deleted.', 'success')
    if current_user.is_admin:
        return redirect(request.referrer or url_for('admin_dashboard'))
    return redirect(url_for('channel', username=current_user.username))


# ---------------------------------------------------------------------------
# Interaction Routes (JSON API)
# ---------------------------------------------------------------------------

@app.route('/api/like/<video_id>', methods=['POST'])
@login_required
def toggle_like(video_id):
    video = Video.query.filter_by(uuid=video_id, is_deleted=False).first_or_404()
    action = request.json.get('action', 'like')  # 'like' or 'dislike'

    existing = Like.query.filter_by(user_id=current_user.id, video_id=video.id).first()
    if existing:
        if existing.type == action:
            db.session.delete(existing)
            result = 'removed'
        else:
            existing.type = action
            result = 'changed'
    else:
        like = Like(user_id=current_user.id, video_id=video.id, type=action)
        db.session.add(like)
        result = 'added'
    db.session.commit()

    return jsonify({
        'result': result,
        'likes': video.like_count,
        'dislikes': video.dislike_count,
        'user_like': Like.query.filter_by(
            user_id=current_user.id, video_id=video.id
        ).first().type if Like.query.filter_by(
            user_id=current_user.id, video_id=video.id
        ).first() else None
    })


@app.route('/api/subscribe/<int:channel_id>', methods=['POST'])
@login_required
def toggle_subscribe(channel_id):
    channel = db.session.get(User, channel_id)
    if not channel or channel.id == current_user.id:
        return jsonify({'error': 'Invalid'}), 400

    existing = Subscription.query.filter_by(
        subscriber_id=current_user.id, channel_id=channel_id
    ).first()

    if existing:
        db.session.delete(existing)
        subscribed = False
    else:
        sub = Subscription(subscriber_id=current_user.id, channel_id=channel_id)
        db.session.add(sub)
        subscribed = True
    db.session.commit()

    return jsonify({'subscribed': subscribed, 'count': channel.subscriber_count})


@app.route('/api/comment/<video_id>', methods=['POST'])
@login_required
def add_comment(video_id):
    video = Video.query.filter_by(uuid=video_id, is_deleted=False).first_or_404()
    content = request.json.get('content', '').strip()
    parent_id = request.json.get('parent_id')

    if not content or len(content) > 2000:
        return jsonify({'error': 'Invalid comment'}), 400

    comment = Comment(
        user_id=current_user.id,
        video_id=video.id,
        parent_id=parent_id or None,
        content=content
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'id': comment.id,
        'content': comment.content,
        'username': current_user.username,
        'avatar': current_user.avatar_url(),
        'time': comment.time_ago(),
        'parent_id': comment.parent_id
    })


@app.route('/api/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({'error': 'Not found'}), 404
    if comment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    comment.is_deleted = True
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/report', methods=['POST'])
@login_required
def report_content():
    data = request.json
    content_type = data.get('content_type')
    content_id = data.get('content_id')
    reason = data.get('reason', '').strip()

    if content_type not in ('video', 'comment') or not content_id or not reason:
        return jsonify({'error': 'Invalid'}), 400

    report = Report(
        reporter_id=current_user.id,
        content_type=content_type,
        reason=reason[:200]
    )
    if content_type == 'video':
        video = Video.query.filter_by(uuid=content_id).first_or_404()
        report.video_id = video.id
    else:
        report.comment_id = int(content_id)

    db.session.add(report)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Channel Routes
# ---------------------------------------------------------------------------

@app.route('/channel/<username>')
def channel(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'videos')

    videos = Video.query.filter_by(user_id=user.id, is_deleted=False)\
        .order_by(desc(Video.created_at))\
        .paginate(page=page, per_page=20, error_out=False)

    is_subscribed = False
    if current_user.is_authenticated and current_user.id != user.id:
        is_subscribed = Subscription.query.filter_by(
            subscriber_id=current_user.id, channel_id=user.id
        ).first() is not None

    return render_template('channel/profile.html', channel_user=user,
                           videos=videos, is_subscribed=is_subscribed, tab=tab)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'profile':
            bio = request.form.get('bio', '').strip()[:500]
            current_user.bio = bio

            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename and allowed_file(avatar_file.filename, ALLOWED_THUMB):
                fname = save_file(avatar_file, 'avatars')
                current_user.avatar = fname

            db.session.commit()
            flash('Profile updated.', 'success')

        elif action == 'password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'error')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'error')
            elif len(new_pw) < 6:
                flash('Password must be at least 6 characters.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed.', 'success')

        return redirect(url_for('settings'))

    return render_template('settings.html')


# ---------------------------------------------------------------------------
# Admin Routes
# ---------------------------------------------------------------------------

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    tab = request.args.get('tab', 'overview')
    stats = {
        'users': User.query.count(),
        'videos': Video.query.filter_by(is_deleted=False).count(),
        'comments': Comment.query.filter_by(is_deleted=False).count(),
        'reports': Report.query.filter_by(is_resolved=False).count(),
    }
    users = None
    videos = None
    reports = None
    comments = None

    if tab == 'users':
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '')
        query = User.query
        if q:
            query = query.filter(User.username.ilike(f'%{q}%') | User.email.ilike(f'%{q}%'))
        users = query.order_by(desc(User.created_at)).paginate(page=page, per_page=30, error_out=False)

    elif tab == 'videos':
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '')
        query = Video.query.filter_by(is_deleted=False)
        if q:
            query = query.filter(Video.title.ilike(f'%{q}%'))
        videos = query.order_by(desc(Video.created_at)).paginate(page=page, per_page=30, error_out=False)

    elif tab == 'reports':
        page = request.args.get('page', 1, type=int)
        reports = Report.query.filter_by(is_resolved=False)\
            .order_by(desc(Report.created_at))\
            .paginate(page=page, per_page=30, error_out=False)

    elif tab == 'comments':
        page = request.args.get('page', 1, type=int)
        comments = Comment.query.filter_by(is_deleted=False)\
            .order_by(desc(Comment.created_at))\
            .paginate(page=page, per_page=30, error_out=False)

    return render_template('admin/dashboard.html', stats=stats, tab=tab,
                           users=users, videos=videos, reports=reports,
                           comments=comments)


@app.route('/admin/suspend_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_suspend_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        flash('Cannot modify this user.', 'error')
        return redirect(url_for('admin_dashboard', tab='users'))
    user.is_suspended = not user.is_suspended
    db.session.commit()
    action = 'suspended' if user.is_suspended else 'unsuspended'
    flash(f'User {user.username} has been {action}.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='users'))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        flash('Cannot delete this user.', 'error')
        return redirect(url_for('admin_dashboard', tab='users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin_dashboard', tab='users'))


@app.route('/admin/delete_video/<int:video_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_video(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        flash('Video not found.', 'error')
        return redirect(url_for('admin_dashboard', tab='videos'))
    video.is_deleted = True
    db.session.commit()
    flash('Video removed.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='videos'))


@app.route('/admin/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('Comment not found.', 'error')
        return redirect(url_for('admin_dashboard'))
    comment.is_deleted = True
    db.session.commit()
    flash('Comment removed.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='comments'))


@app.route('/admin/resolve_report/<int:report_id>', methods=['POST'])
@login_required
@admin_required
def admin_resolve_report(report_id):
    report = db.session.get(Report, report_id)
    if report:
        report.is_resolved = True
        db.session.commit()
    return redirect(request.referrer or url_for('admin_dashboard', tab='reports'))


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           message='You do not have permission to access this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           message='The page you were looking for does not exist.'), 404


@app.errorhandler(413)
def too_large(e):
    return render_template('error.html', code=413,
                           message='The file you tried to upload is too large.'), 413


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def create_dirs():
    for d in ['videos', 'audio', 'thumbnails', 'avatars']:
        os.makedirs(os.path.join(UPLOAD_FOLDER, d), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static', 'img'), exist_ok=True)


if __name__ == '__main__':
    with app.app_context():
        create_dirs()
        db.create_all()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
