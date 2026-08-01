import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template_string, request, redirect, url_for, 
    session, send_from_directory, flash, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'groundtube_secret_key_2026')

# Configurare upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mp3', 'wav', 'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Limit 500MB per upload

DB_FILE = 'groundtube.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Tabela Utilizatori
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabela Videoclipuri / Audio
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        user_id INTEGER NOT NULL,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # Tabela Comentarii
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES videos (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # Tabela Abonamente (Subscriptions)
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        UNIQUE(subscriber_id, channel_id)
    )''')

    # Creare cont Master Admin implicit dacă nu există
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = generate_password_hash('admin123')
        c.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin@groundtube.local', admin_pass, 'admin'))

    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- TEMPLATE HTML/CSS/JS INTEGRAL ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GroundTube - Freedom & Video Sharing</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0f0f0f; color: #f1f1f1; padding-bottom: 60px; }
        
        /* Header Desktop & Mobile */
        header { display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; background-color: #0f0f0f; border-bottom: 1px solid #272727; position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 22px; font-weight: 800; color: #ff0000; text-decoration: none; letter-spacing: -1px; }
        .logo span { color: #ffffff; }
        
        .search-form { display: flex; width: 45%; max-width: 600px; }
        .search-form input { width: 100%; padding: 10px 16px; background: #121212; border: 1px solid #303030; color: #fff; border-radius: 40px 0 0 40px; font-size: 14px; outline: none; }
        .search-form input:focus { border-color: #1c62b9; }
        .search-form button { padding: 10px 20px; background: #222222; border: 1px solid #303030; border-left: none; color: #fff; border-radius: 0 40px 40px 0; cursor: pointer; }
        
        .user-nav { display: flex; align-items: center; gap: 12px; }
        .btn { padding: 8px 16px; border-radius: 20px; text-decoration: none; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
        .btn-primary { background-color: #cc0000; color: white; }
        .btn-secondary { background-color: #272727; color: white; }
        .btn-admin { background-color: #eab308; color: black; }

        /* Mobile Bottom Nav */
        .bottom-nav { display: none; position: fixed; bottom: 0; left: 0; width: 100%; background: #0f0f0f; border-top: 1px solid #272727; justify-content: space-around; padding: 10px 0; z-index: 1000; }
        .bottom-nav a { color: #aaa; text-decoration: none; font-size: 12px; text-align: center; }

        /* Categorii Banner */
        .categories { display: flex; gap: 10px; padding: 12px 24px; overflow-x: auto; background: #0f0f0f; border-bottom: 1px solid #272727; }
        .cat-chip { padding: 6px 14px; background: #272727; border-radius: 8px; color: #fff; text-decoration: none; font-size: 13px; white-space: nowrap; }
        .cat-chip:hover { background: #3f3f3f; }

        /* Container Principal */
        .container { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        
        /* Card Video */
        .video-card { background: #0f0f0f; border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; display: flex; flex-direction: column; }
        .thumbnail-box { width: 100%; aspect-ratio: 16/9; background: #1f1f1f; display: flex; align-items: center; justify-content: center; position: relative; border-radius: 12px; overflow: hidden; }
        .thumbnail-box video, .thumbnail-box audio { width: 100%; height: 100%; object-fit: cover; }
        .play-icon { font-size: 36px; color: #ff0000; }
        
        .video-details { padding: 12px 4px; }
        .video-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; line-height: 1.3; color: #f1f1f1; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .video-meta { font-size: 13px; color: #aaaaaa; }

        /* Pagina Watch Video */
        .watch-container { display: flex; flex-wrap: wrap; gap: 24px; }
        .main-player { flex: 2; min-width: 320px; }
        .player-wrapper { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 12px; overflow: hidden; }
        .player-wrapper video { width: 100%; height: 100%; }
        .player-wrapper audio { width: 100%; margin-top: 20%; }
        
        .watch-title { font-size: 20px; font-weight: 700; margin: 16px 0 8px 0; }
        .watch-actions { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #272727; padding-bottom: 16px; }
        .action-btns { display: flex; gap: 10px; }
        .desc-box { background: #272727; padding: 14px; border-radius: 12px; margin-top: 16px; font-size: 14px; }

        /* Comentarii */
        .comments-section { margin-top: 24px; }
        .comment-input { width: 100%; padding: 10px; background: transparent; border: none; border-bottom: 1px solid #383838; color: white; outline: none; margin-bottom: 10px; }
        .comment-card { background: #181818; padding: 12px; border-radius: 8px; margin-bottom: 10px; }

        /* Formular Upload / Auth */
        .form-box { max-width: 500px; margin: 40px auto; background: #181818; padding: 30px; border-radius: 12px; border: 1px solid #272727; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #aaa; }
        .form-control { width: 100%; padding: 10px; background: #0f0f0f; border: 1px solid #303030; border-radius: 6px; color: white; }

        @media (max-width: 768px) {
            .search-form { display: none; }
            .bottom-nav { display: flex; }
            .container { padding: 12px; }
        }
    </style>
</head>
<body>

    <header>
        <a href="/" class="logo">Ground<span>Tube</span></a>
        
        <form class="search-form" action="/" method="GET">
            <input type="text" name="q" placeholder="Caută videoclipuri sau piese audio..." value="{{ search_query or '' }}">
            <button type="submit">🔍</button>
        </form>

        <div class="user-nav">
            {% if session.get('user_id') %}
                <a href="/upload" class="btn btn-primary">+ Upload</a>
                {% if session.get('role') == 'admin' %}
                    <a href="/admin" class="btn btn-admin">Admin Panel</a>
                {% endif %}
                <a href="/logout" class="btn btn-secondary">Logout ({{ session.get('username') }})</a>
            {% else %}
                <a href="/login" class="btn btn-secondary">Conectare</a>
                <a href="/register" class="btn btn-primary">Înregistrare</a>
            {% endif %}
        </div>
    </header>

    <div class="categories">
        <a href="/" class="cat-chip">Toate</a>
        <a href="/?cat=Muzica" class="cat-chip">🎵 Muzică & Trap</a>
        <a href="/?cat=Gaming" class="cat-chip">🎮 Gaming</a>
        <a href="/?cat=Podcasts" class="cat-chip">🎙️ Podcasts</a>
        <a href="/?cat=Tech" class="cat-chip">💻 Tech & Code</a>
    </div>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div style="padding: 12px; background: #22c55e; color: black; font-weight: bold; border-radius: 6px; margin-bottom: 16px;">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <!-- Mobile Bottom Navigation -->
    <div class="bottom-nav">
        <a href="/">🏠<br>Acasă</a>
        <a href="/upload">➕<br>Upload</a>
        {% if session.get('user_id') %}
            <a href="/logout">👤<br>Profil</a>
        {% else %}
            <a href="/login">🔑<br>Login</a>
        {% endif %}
    </div>

</body>
</html>
"""

# --- RUTE PRINCIPALE ---

@app.route('/')
def index():
    query = request.args.get('q', '')
    category = request.args.get('cat', '')
    
    conn = get_db()
    c = conn.cursor()
    
    sql = "SELECT videos.*, users.username FROM videos JOIN users ON videos.user_id = users.id WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%'])
    if category:
        sql += " AND category = ?"
        params.append(category)
        
    sql += " ORDER BY videos.id DESC"
    c.execute(sql, params)
    videos = c.fetchall()
    conn.close()

    content = """
    <div class="video-grid">
        {% for video in videos %}
        <a href="/watch/{{ video.id }}" class="video-card">
            <div class="thumbnail-box">
                <span class="play-icon">
                    {% if video.file_type in ['mp3', 'wav'] %}🎵{% else %}▶{% endif %}
                </span>
            </div>
            <div class="video-details">
                <div class="video-title">{{ video.title }}</div>
                <div class="video-meta">{{ video.username }} • {{ video.views }} vizionări</div>
            </div>
        </a>
        {% else %}
        <p style="color: #aaa;">Nu a fost găsit niciun videoclip sau piesă audio. Încarcă tu primul fișier!</p>
        {% endfor %}
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content), videos=videos, search_query=query)

@app.route('/watch/<int:video_id>')
def watch(video_id):
    conn = get_db()
    c = conn.cursor()
    
    # Update vizionări
    c.execute("UPDATE videos SET views = views + 1 WHERE id = ?", (video_id,))
    conn.commit()

    c.execute("SELECT videos.*, users.username FROM videos JOIN users ON videos.user_id = users.id WHERE videos.id = ?", (video_id,))
    video = c.fetchone()

    if not video:
        conn.close()
        return "Videoclipul nu a fost găsit", 404

    # Preluare comentarii
    c.execute("SELECT comments.*, users.username FROM comments JOIN users ON comments.user_id = users.id WHERE video_id = ? ORDER BY id DESC", (video_id,))
    comments = c.fetchall()
    conn.close()

    content = """
    <div class="watch-container">
        <div class="main-player">
            <div class="player-wrapper">
                {% if video.file_type in ['mp3', 'wav'] %}
                    <audio controls autoplay style="width: 90%; margin: 15% 5%;">
                        <source src="/uploads/{{ video.filename }}" type="audio/{{ video.file_type }}">
                    </audio>
                {% else %}
                    <video controls autoplay>
                        <source src="/uploads/{{ video.filename }}" type="video/{{ video.file_type }}">
                    </video>
                {% endif %}
            </div>
            <h1 class="watch-title">{{ video.title }}</h1>
            <div class="watch-actions">
                <div><strong>{{ video.username }}</strong> • {{ video.views }} vizionări</div>
                <div class="action-btns">
                    <a href="/like/{{ video.id }}" class="btn btn-secondary">👍 {{ video.likes }}</a>
                    <a href="/dislike/{{ video.id }}" class="btn btn-secondary">👎 {{ video.dislikes }}</a>
                </div>
            </div>
            <div class="desc-box">
                <p><strong>Categorie:</strong> {{ video.category }}</p>
                <p style="margin-top: 8px;">{{ video.description or 'Fără descriere.' }}</p>
            </div>

            <!-- Secțiune Comentarii -->
            <div class="comments-section">
                <h3>Comentarii</h3>
                {% if session.get('user_id') %}
                <form action="/comment/{{ video.id }}" method="POST" style="margin-top: 12px;">
                    <input type="text" name="content" class="comment-input" placeholder="Adaugă un comentariu public..." required>
                    <button type="submit" class="btn btn-primary" style="float: right;">Trimite</button>
                </form>
                <div style="clear: both;"></div>
                {% else %}
                <p style="color: #aaa; margin: 10px 0;"><a href="/login" style="color: #ff0000;">Conectează-te</a> pentru a lăsa un comentariu.</p>
                {% endif %}

                <div style="margin-top: 20px;">
                    {% for c in comments %}
                    <div class="comment-card">
                        <strong>{{ c.username }}</strong>
                        <p style="margin-top: 4px; font-size: 14px;">{{ c.content }}</p>
                    </div>
                    {% else %}
                    <p style="color: #888; font-size: 14px;">Niciun comentariu încă.</p>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content), video=video, comments=comments)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('user_id'):
        flash('Trebuie să fii conectat pentru a încărca fișiere!')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        file = request.files.get('file')

        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO videos (title, description, filename, file_type, category, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                      (title, description, filename, ext, category, session['user_id']))
            conn.commit()
            conn.close()

            flash('Fișierul a fost încărcat cu succes!')
            return redirect(url_for('index'))
        else:
            flash('Format de fișier neacceptat! Trimite MP4, WEBM, MP3 sau WAV.')

    content = """
    <div class="form-box">
        <h2 style="margin-bottom: 20px;">Upload Video / Audio</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>Titlu</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Categorie</label>
                <select name="category" class="form-control">
                    <option value="Muzica">Muzică & Trap</option>
                    <option value="Gaming">Gaming</option>
                    <option value="Podcasts">Podcasts</option>
                    <option value="Tech">Tech & Code</option>
                </select>
            </div>
            <div class="form-group">
                <label>Descriere</label>
                <textarea name="description" class="form-control" rows="3"></textarea>
            </div>
            <div class="form-group">
                <label>Fișier (MP4, WEBM, MP3, WAV)</label>
                <input type="file" name="file" class="form-control" accept="video/*,audio/*" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Publică pe GroundTube</button>
        </form>
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db()
        c = conn.cursor()
        try:
            pwd_hash = generate_password_hash(password)
            c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, pwd_hash))
            conn.commit()
            flash('Cont creat cu succes! Te poți conecta.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Numele de utilizator sau emailul există deja!')
        finally:
            conn.close()

    content = """
    <div class="form-box">
        <h2 style="margin-bottom: 20px;">Înregistrare GroundTube</h2>
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Parolă</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Creează Cont</button>
        </form>
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Conectare reușită!')
            return redirect(url_for('index'))
        else:
            flash('Utilizator sau parolă incorectă!')

    content = """
    <div class="form-box">
        <h2 style="margin-bottom: 20px;">Conectare</h2>
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label>Parolă</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Conectare</button>
        </form>
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content))

@app.route('/logout')
def logout():
    session.clear()
    flash('Te-ai deconectat.')
    return redirect(url_for('index'))

@app.route('/comment/<int:video_id>', methods=['POST'])
def add_comment(video_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    content = request.form.get('content')
    if content:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO comments (video_id, user_id, content) VALUES (?, ?, ?)", (video_id, session['user_id'], content))
        conn.commit()
        conn.close()
    return redirect(url_for('watch', video_id=video_id))

@app.route('/like/<int:video_id>')
def like(video_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE videos SET likes = likes + 1 WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('watch', video_id=video_id))

@app.route('/dislike/<int:video_id>')
def dislike(video_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE videos SET dislikes = dislikes + 1 WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('watch', video_id=video_id))

# --- MASTER ADMIN PANEL ---
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        flash('Acces interzis! Doar Master Admin are acces.')
        return redirect(url_for('index'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT videos.*, users.username FROM videos JOIN users ON videos.user_id = users.id")
    videos = c.fetchall()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    content = """
    <h2>Master Admin Control Panel</h2>
    <div style="margin-top: 20px;">
        <h3>Gestionare Videoclipuri</h3>
        <table style="width: 100%; margin-top: 10px; border-collapse: collapse; background: #181818;">
            <tr style="border-bottom: 1px solid #333; text-align: left; padding: 8px;">
                <th style="padding: 10px;">ID</th><th>Titlu</th><th>Autor</th><th>Acțiuni</th>
            </tr>
            {% for v in videos %}
            <tr style="border-bottom: 1px solid #222;">
                <td style="padding: 10px;">{{ v.id }}</td>
                <td>{{ v.title }}</td>
                <td>{{ v.username }}</td>
                <td><a href="/admin/delete_video/{{ v.id }}" class="btn btn-primary" style="padding: 4px 8px; font-size: 12px;">Șterge</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', content), videos=videos, users=users)

@app.route('/admin/delete_video/<int:video_id>')
def delete_video(video_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    flash('Videoclip șters de Admin.')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
