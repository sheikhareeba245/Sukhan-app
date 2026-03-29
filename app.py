from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import random
import sqlite3
import os
import time
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'sukhan-secret-key-2024'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DB = 'sukhan.db'

ai_lines = {
    'love': [
        'جب دنیا سے تھک کر وہ میرے پاس آتا ہے',
        'محبت وہ زبان ہے جو دل خود بولتا ہے',
        'اُس کی آنکھوں میں میری پوری کائنات ہے',
    ],
    'reality': [
        'زندگی وہ نہیں جو ہم سوچتے ہیں',
        'سچ کا سامنا کرنا ہی اصل بہادری ہے',
        'ہر لمحہ اپنے اندر ایک سبق چھپائے ہے',
    ],
    'happy': [
        'خوشی وہ پھول ہے جو دل کے باغ میں کھلتا ہے',
        'ہنسی وہ موسیقی ہے جو روح کو تازہ کرتی ہے',
        'چھوٹی چھوٹی خوشیاں ہی زندگی کا سرمایہ ہیں',
    ],
    'sad': [
        'کچھ درد ایسے ہوتے ہیں جو لفظوں میں نہیں آتے',
        'آنسو وہ باتیں کہتے ہیں جو ہونٹ نہیں کہہ سکتے',
        'تنہائی میں بھی ایک عجیب سکون ہوتا ہے',
    ],
    'dosti': [
    'سچی دوستی وہ ہے جو وقت کے ساتھ اور گہری ہو جائے',
    'دوست وہ ہے جو تمہاری خاموشی بھی سمجھ لے',
    'یاریاں وہ خزانہ ہیں جو پیسوں سے نہیں ملتیں',
],
}

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            mood    TEXT NOT NULL,
            title   TEXT NOT NULL,
            content TEXT NOT NULL,
            image   TEXT DEFAULT NULL,
            created TEXT DEFAULT (date('now'))
        )
    ''')
    try:
        c.execute('ALTER TABLE poems ADD COLUMN image TEXT DEFAULT NULL')
    except:
        pass
    try:
        c.execute('ALTER TABLE poems ADD COLUMN user_id INTEGER DEFAULT 1')
    except:
        pass
    try:
        c.execute('ALTER TABLE poems ADD COLUMN is_public INTEGER DEFAULT 0')
    except:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS streak (
            id      INTEGER PRIMARY KEY,
            last_written TEXT,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR IGNORE INTO streak (id, last_written, current_streak, longest_streak) VALUES (1, NULL, 0, 0)')

    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            poem_id  INTEGER UNIQUE,
            added    TEXT DEFAULT (date('now'))
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created  TEXT DEFAULT (date('now'))
        )
    ''')
    conn.commit()
    conn.close()

def get_poem_count(mood):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM poems WHERE mood = ?', (mood,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_streak():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT last_written, current_streak, longest_streak FROM streak WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return {
        'last_written': row[0],
        'current': row[1],
        'longest': row[2]
    }

def update_streak():
    from datetime import date, timedelta
    today = str(date.today())
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT last_written, current_streak, longest_streak FROM streak WHERE id = 1')
    row = c.fetchone()
    last_written = row[0]
    current = row[1]
    longest = row[2]

    if last_written == today:
        # Already written today!
        pass
    elif last_written == str(date.today() - timedelta(days=1)):
        # Yesterday — streak continues!
        current += 1
        if current > longest:
            longest = current
        c.execute('UPDATE streak SET last_written=?, current_streak=?, longest_streak=? WHERE id=1',
                  (today, current, longest))
    else:
        # Streak broken — start fresh
        current = 1
        c.execute('UPDATE streak SET last_written=?, current_streak=?, longest_streak=? WHERE id=1',
                  (today, current, longest))

    conn.commit()
    conn.close()

def is_favorite(poem_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id FROM favorites WHERE poem_id = ?', (poem_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

@app.route('/favorite/<int:poem_id>/<mood>')
def favorite(poem_id, mood):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if is_favorite(poem_id):
        c.execute('DELETE FROM favorites WHERE poem_id = ?', (poem_id,))
    else:
        c.execute('INSERT INTO favorites (poem_id) VALUES (?)', (poem_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('section', key=mood))

@app.route('/favorites')
def favorites():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT p.id, p.mood, p.title, p.content, p.created, p.image
                 FROM poems p
                 JOIN favorites f ON p.id = f.poem_id
                 ORDER BY f.added DESC''')
    poems = c.fetchall()
    conn.close()
    return render_template('favorites.html', poems=poems)

@app.route('/profile')
def profile():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Total poems
    c.execute('SELECT COUNT(*) FROM poems')
    total_poems = c.fetchone()[0]
    
    # Poems per mood
    c.execute('SELECT mood, COUNT(*) FROM poems GROUP BY mood')
    mood_counts = dict(c.fetchall())
    
    # Total favorites
    c.execute('SELECT COUNT(*) FROM favorites')
    total_favs = c.fetchone()[0]
    
    # Most written mood
    c.execute('SELECT mood, COUNT(*) as cnt FROM poems GROUP BY mood ORDER BY cnt DESC LIMIT 1')
    top_mood = c.fetchone()
    
    conn.close()
    streak = get_streak()
    
    return render_template('profile.html',
        total_poems=total_poems,
        mood_counts=mood_counts,
        total_favs=total_favs,
        top_mood=top_mood,
        streak=streak
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        hashed   = generate_password_hash(password)
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                      (username, email, hashed))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            return render_template('register.html', error='Username ya email already exists!')
    return render_template('register.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT id, username, email, password FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('home'))
        return render_template('login.html', error='Email ya password galat hai!')
    return render_template('login.html', error=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    from datetime import date
    today = date.today()
    mood_of_day_list = ['love', 'reality', 'happy', 'sad', 'dosti']
    motd_key = mood_of_day_list[today.day % len(mood_of_day_list)]
    motd_emojis = {
        'love': '🌹', 'reality': '🌍',
        'happy': '😊', 'sad': '💔', 'dosti': '🤝'
    }
    motd_urdu = {
        'love': 'محبت', 'reality': 'حقیقت',
        'happy': 'خوشی', 'sad': 'غم', 'dosti': 'دوستی'
    }
    mood_of_day = {
        'key': motd_key,
        'emoji': motd_emojis[motd_key],
        'label': motd_key.title(),
        'urdu': motd_urdu[motd_key],
        'line': random.choice(ai_lines[motd_key])
    }
    sections = [
        {
            'key': 'love',
            'label': 'Love',
            'emoji': '🌹',
            'tagline': 'جہاں دل اپنی زبان میں بولتا ہے',
            'poem_count': get_poem_count('love'),
            'ai_line': random.choice(ai_lines['love'])
        },
        {
            'key': 'reality',
            'label': 'Reality',
            'emoji': '🌍',
            'tagline': 'سچ جو کہنا ضروری ہے',
            'poem_count': get_poem_count('reality'),
            'ai_line': random.choice(ai_lines['reality'])
        },
        {
            'key': 'happy',
            'label': 'Happy',
            'emoji': '😊',
            'tagline': 'خوشی کے لمحوں کی یادیں',
            'poem_count': get_poem_count('happy'),
            'ai_line': random.choice(ai_lines['happy'])
        },
        {
            'key': 'sad',
            'label': 'Sad',
            'emoji': '💔',
            'tagline': 'وہ درد جو لفظ بن جاتا ہے',
            'poem_count': get_poem_count('sad'),
            'ai_line': random.choice(ai_lines['sad'])
        },
        {
            'key': 'dosti',
            'label': 'Dosti',
            'emoji': '🤝',
            'tagline': 'وہ رشتہ جو خون سے نہیں دل سے بنتا ہے',
            'poem_count': get_poem_count('dosti'),
            'ai_line': random.choice(ai_lines['dosti'])
        },
    ]
    streak = get_streak()
    return render_template('index.html', sections=sections, streak=streak, mood_of_day=mood_of_day)

@app.route('/section/<key>')
@login_required
def section(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, title, content, created, image FROM poems WHERE mood = ? AND user_id = ? ORDER BY id DESC',
              (key, current_user.id))
    raw_poems = c.fetchall()
    conn.close()
    poems = []
    for p in raw_poems:
        poems.append({
            'id': p[0], 'title': p[1], 'content': p[2],
            'created': p[3], 'image': p[4],
            'is_fav': is_favorite(p[0])
        })
    ai_line = random.choice(ai_lines.get(key, ['']))
    return render_template('section.html', key=key, poems=poems, ai_line=ai_line)

@app.route('/save', methods=['POST'])
@login_required
def save():
    mood    = request.form['mood']
    title   = request.form['title']
    content = request.form['content']
    image_filename = None
    is_public = 1 if request.form.get('is_public') else 0

    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = str(int(time.time())) + '_' + filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

    if title and content:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO poems (user_id, mood, title, content, image, is_public) VALUES (?, ?, ?, ?, ?, ?)',
                  (current_user.id, mood, title, content, image_filename, is_public))
        conn.commit()
        conn.close()
        update_streak()
    return redirect(url_for('section', key=mood))

@app.route('/explore')
@login_required
def explore():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT p.id, p.mood, p.title, p.content, p.created, p.image, u.username
                 FROM poems p
                 JOIN users u ON p.user_id = u.id
                 WHERE p.is_public = 1
                 ORDER BY p.id DESC''')
    poems = c.fetchall()
    conn.close()
    return render_template('explore.html', poems=poems)

@app.route('/delete/<int:poem_id>/<mood>')
def delete(poem_id, mood):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM poems WHERE id = ?', (poem_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('section', key=mood))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = []
    if query:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''SELECT id, mood, title, content, created, image 
                     FROM poems 
                     WHERE title LIKE ? OR content LIKE ?
                     ORDER BY id DESC''',
                  (f'%{query}%', f'%{query}%'))
        results = c.fetchall()
        conn.close()
    return render_template('search.html', query=query, results=results)

@app.route('/card/<int:poem_id>')
def card(poem_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, mood, title, content, created, image FROM poems WHERE id = ?', (poem_id,))
    row = c.fetchone()
    conn.close()
    poem = {
        'id': row[0], 'mood': row[1], 'title': row[2],
        'content': row[3], 'created': row[4], 'image': row[5]
    }
    return render_template('card.html', poem=poem)

@app.route('/edit/<int:poem_id>')
def edit(poem_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, mood, title, content FROM poems WHERE id = ?', (poem_id,))
    row = c.fetchone()
    conn.close()
    poem = {
        'id': row[0], 'mood': row[1], 'title': row[2], 'content': row[3]
    }
    return render_template('edit.html', poem=poem)

@app.route('/update/<int:poem_id>', methods=['POST'])
def update(poem_id):
    title   = request.form['title']
    content = request.form['content']
    mood    = request.form['mood']
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Handle new image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and allowed_file(file.filename):
            import time
            filename = str(int(time.time())) + '_' + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            c.execute('UPDATE poems SET title=?, content=?, image=? WHERE id=?',
                      (title, content, filename, poem_id))
        else:
            c.execute('UPDATE poems SET title=?, content=? WHERE id=?',
                      (title, content, poem_id))
    else:
        c.execute('UPDATE poems SET title=?, content=? WHERE id=?',
                  (title, content, poem_id))
    
    conn.commit()
    conn.close()
    return redirect(url_for('section', key=mood))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    init_db()
    app.run(debug=True)