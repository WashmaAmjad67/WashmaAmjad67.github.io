"""Washma portfolio: server-rendered site, persistent CMS, and session-protected administration."""
from __future__ import annotations
import os, json, sqlite3, secrets, time, re, io, hashlib, threading, warnings
from pathlib import Path
from functools import wraps
from urllib.parse import urlsplit
from datetime import timedelta
from flask import Flask, request, session, jsonify, render_template, send_from_directory, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from PIL import Image, UnidentifiedImageError

os.umask(0o077)
ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS = DATA / 'uploads'; UPLOADS.mkdir(exist_ok=True)
DB = DATA / 'portfolio.sqlite3'
secret_path = DATA / '.session-secret'
if not secret_path.exists():
    try:
        with open(secret_path, 'x') as f: f.write(secrets.token_hex(48))
        secret_path.chmod(0o600)
    except FileExistsError: pass
app = Flask(__name__, static_folder=None, template_folder=str(ROOT / 'templates'))
app.config.update(SECRET_KEY=secret_path.read_text().strip(), MAX_CONTENT_LENGTH=11*1024*1024,
    SESSION_COOKIE_NAME='washma_admin', SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
    SESSION_COOKIE_SECURE=os.environ.get('SECURE_COOKIES') == '1', PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
PAGES = {'home':'index.html','about':'about.html','portfolio':'portfolio.html','services':'services.html','awards':'awards.html','contact':'contact.html'}
THEMES = {
    'charcoal': {'name':'Charcoal Orange','primary':'#ff763c','secondary':'#4884ff','background':'#111214','panel':'#191a1d','text':'#f1f0ed','muted':'#97989d'},
    'midnight': {'name':'Midnight Blue','primary':'#69a8ff','secondary':'#e9ad79','background':'#0b1324','panel':'#152038','text':'#eef4ff','muted':'#9caec8'},
    'purple': {'name':'Slate Purple','primary':'#bc9aff','secondary':'#78b8e0','background':'#161521','panel':'#242134','text':'#f3efff','muted':'#aaa4c0'},
    'emerald': {'name':'Emerald Dark','primary':'#67dcb1','secondary':'#e5bd78','background':'#0e1918','panel':'#192b27','text':'#edf8f1','muted':'#9cb9ac'},
}
SEED = json.loads((ROOT / 'seed.json').read_text())
condition = threading.Condition()
event_slots = threading.BoundedSemaphore(16)

def db():
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=15000')
    return conn

def initialize():
    with db() as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript('''CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY CHECK(id=1), document TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL, auth_version INTEGER NOT NULL DEFAULT 1, must_change INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS attempts (address TEXT PRIMARY KEY, failures INTEGER NOT NULL, started REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, action TEXT NOT NULL, created REAL NOT NULL);''')
        if not conn.execute('SELECT 1 FROM content').fetchone(): conn.execute('INSERT INTO content VALUES (1,?)', (json.dumps(SEED),))
        if not conn.execute('SELECT 1 FROM users').fetchone(): conn.execute('INSERT INTO users(username,password) VALUES (?,?)', ('admin',generate_password_hash('Admin@123')))
initialize()

def document():
    with db() as conn: return json.loads(conn.execute('SELECT document FROM content WHERE id=1').fetchone()[0])

def audit(conn, action):
    conn.execute('INSERT INTO audit(action,created) VALUES (?,?)',(action,time.time()))
    conn.execute('DELETE FROM audit WHERE id NOT IN (SELECT id FROM audit ORDER BY id DESC LIMIT 200)')

def user():
    if 'uid' not in session: return None
    with db() as conn: u=conn.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone()
    if not u or u['auth_version'] != session.get('auth_version'): session.clear(); return None
    return u

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not user(): return jsonify(error='Please log in to continue.'),401
        if request.method not in ('GET','HEAD') and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','missing')):
            return jsonify(error='Security token expired. Reload the Admin Panel.'),403
        return fn(*args,**kwargs)
    return wrapped

@app.before_request
def request_security():
    if request.method in ('POST','PUT','PATCH','DELETE'):
        origin=request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host: abort(403, description='Cross-site requests are not allowed.')
        if request.headers.get('Sec-Fetch-Site') == 'cross-site': abort(403)
    if request.path.startswith('/api/admin') and request.is_json and request.content_length and request.content_length>2*1024*1024:
        abort(413)

@app.after_request
def response_security(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self' mailto:"
    if response.mimetype in ('text/html','text/css','application/json') or request.path.startswith('/api'):
        response.headers['Cache-Control']='no-store'
    return response

@app.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith('/api/'): return jsonify(error=error.description),error.code
    return render_template('error.html',code=error.code,message=error.description),error.code

@app.errorhandler(ValueError)
def validation_error(error): return jsonify(error=str(error)),400

def text(value, label, max_len=6000, required=False):
    if not isinstance(value,str) or len(value)>max_len or '\x00' in value: raise ValueError(f'{label}: enter text up to {max_len} characters.')
    if required and not value.strip(): raise ValueError(f'{label} is required.')
    return value

def image_url(value):
    text(value,'Image path',300,True)
    if re.fullmatch(r'/uploads/[a-f0-9]{32}\.webp',value):
        if not (UPLOADS / value.rsplit('/',1)[1]).is_file(): raise ValueError('Uploaded image is missing.')
    elif value.startswith('assets/'):
        target=(ROOT/value).resolve()
        if not target.is_relative_to(ROOT/'assets') or not target.is_file(): raise ValueError('Image must be a bundled asset or an uploaded image.')
    else: raise ValueError('Use the image uploader to add an image.')
    return value

def validate(doc):
    if not isinstance(doc,dict): raise ValueError('Invalid site content.')
    if set(doc) != set(SEED): raise ValueError('Site content structure is incomplete.')
    if doc['theme'] not in THEMES: raise ValueError('Choose a supported theme.')
    settings=doc['settings']
    if not isinstance(settings,dict) or set(settings)!=set(SEED['settings']): raise ValueError('Contact settings are incomplete.')
    for key,value in settings.items(): text(value,key,500)
    if not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',settings['email']) or len(settings['email'])>160: raise ValueError('Enter a valid contact email.')
    text(settings['brand'],'Brand name',40,True);text(settings['name'],'Name',100,True)
    if settings['whatsapp'] and not re.fullmatch(r'\+[1-9][0-9]{6,14}',settings['whatsapp']): raise ValueError('WhatsApp: use + followed by country code and number, with no spaces.')
    for key in ('instagram','youtube','tiktok','fiverr','linkedin','behance'):
        if settings[key]:
            url=urlsplit(settings[key])
            if url.scheme!='https' or not url.hostname or url.username or url.password or any(ch.isspace() for ch in settings[key]): raise ValueError(f'{key}: use a complete https:// profile URL.')
    if set(doc['pages'])!=set(SEED['pages']): raise ValueError('All six pages are required.')
    for key,page in doc['pages'].items():
        original=SEED['pages'][key]
        if set(page)!=set(original) or set(page['texts'])!=set(original['texts']) or page['fields']!=original['fields'] or page['title']!=original['title']: raise ValueError('Page field structure cannot be changed.')
        for k,v in page['texts'].items(): text(v,f'{page["title"]} text',6000)
    media=doc['media']
    if not isinstance(media,dict) or len(media)>1000 or 'profile' not in media: raise ValueError('The profile image must remain in the library (up to 1000 images).')
    for key,m in media.items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',key) or set(m)!={'id','name','url','alt'} or m['id']!=key: raise ValueError('Invalid image record.')
        text(m['name'],'Image name',160,True);text(m['alt'],'Image description',500);image_url(m['url'])
    schemas={
        'services':{'id','title','kicker','description','features','price','priceLabel','icon'},
        'projects':{'id','title','description','detail','category','media'},
        'featured':{'id','title','category','description','media'},
        'awards':{'id','year','title','issuer','category','description','meaning','sample','icon'}}
    for collection,keys in schemas.items():
        records=doc[collection]
        if not isinstance(records,list) or len(records)>250: raise ValueError(f'{collection}: maximum 250 entries.')
        ids=set()
        for record in records:
            if not isinstance(record,dict) or set(record)!=keys: raise ValueError(f'{collection}: incomplete entry.')
            for key,v in record.items():
                if key=='features':
                    if not isinstance(v,list) or len(v)>12: raise ValueError('Use up to 12 service features.')
                    for feature in v:text(feature,'Service feature',200,True)
                elif key=='sample':
                    if not isinstance(v,bool): raise ValueError('Sample indicator must be true or false.')
                else:text(v,key,6000 if key in ('description','detail','meaning') else 300,key in ('id','title'))
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',record['id']) or record['id'] in ids: raise ValueError('Entry IDs must be unique.')
            ids.add(record['id'])
            if 'media' in record and record['media'] not in media: raise ValueError('Select an image for every project.')
            if collection=='projects' and record['category'] not in ('long','short','color'): raise ValueError('Choose a valid portfolio category.')
            if collection=='services' and record['icon'] not in ('identity','layout','code','refresh'): raise ValueError('Choose a service icon.')
            if collection=='awards' and record['icon'] not in ('trophy','medal','diamond','check'): raise ValueError('Choose an award icon.')
            if collection=='awards':text(record['year'],'Award year',40,True)
    if not isinstance(doc['revision'],int): raise ValueError('Invalid content revision.')
    return doc

def publish(incoming, theme_only=False):
    expected=request.headers.get('If-Match','')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=json.loads(conn.execute('SELECT document FROM content WHERE id=1').fetchone()[0])
        if str(current['revision'])!=expected: return None
        if theme_only: current['theme']=incoming; new=current
        else:new=incoming
        new=validate(new);new['revision']=current['revision']+1
        conn.execute('UPDATE content SET document=? WHERE id=1',(json.dumps(new),))
        audit(conn,'Theme published' if theme_only else 'Website content published')
    with condition:condition.notify_all()
    return new

@app.get('/api/admin/session')
def session_info():
    u=user()
    if not u:return jsonify(authenticated=False),401
    return jsonify(authenticated=True,username=u['username'],mustChange=bool(u['must_change']),csrf=session['csrf'])

@app.post('/api/admin/login')
def login():
    body=request.get_json(silent=True) or {};address=hashlib.sha256(request.remote_addr.encode()).hexdigest();now=time.time()
    with db() as conn:
        conn.execute('DELETE FROM attempts WHERE started < ?',(now-900,))
        attempt=conn.execute('SELECT * FROM attempts WHERE address=?',(address,)).fetchone()
        if attempt and attempt['failures']>=10:return jsonify(error='Too many login attempts. Try again in 15 minutes.'),429
        username=body.get('username','');password=body.get('password','')
        if not isinstance(username,str) or not isinstance(password,str) or len(username)>80 or len(password)>200:return jsonify(error='Username or password is incorrect.'),401
        u=conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        # Perform a hash check even for unknown usernames.
        valid=check_password_hash(u['password'] if u else generate_password_hash('not-the-password'),password)
        if not u or not valid:
            conn.execute('INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(address) DO UPDATE SET failures=failures+1',(address,now))
            return jsonify(error='Username or password is incorrect.'),401
        conn.execute('DELETE FROM attempts WHERE address=?',(address,))
    session.clear();session.permanent=True;session.update(uid=u['id'],auth_version=u['auth_version'],csrf=secrets.token_urlsafe(32))
    return jsonify(username=u['username'],mustChange=bool(u['must_change']),csrf=session['csrf'])

@app.post('/api/admin/logout')
@admin_required
def logout():session.clear();return jsonify(ok=True)

@app.get('/api/admin/content')
@admin_required
def get_content():return jsonify(content=document(),themes=THEMES)

@app.put('/api/admin/content')
@admin_required
def save_content():
    body=request.get_json(silent=True)
    if not isinstance(body,dict):abort(400)
    new=publish(body)
    if new is None:return jsonify(error='Someone saved a newer version. Reload the saved content before publishing again; copy any unsaved text first.'),409
    return jsonify(content=new)

@app.put('/api/admin/theme')
@admin_required
def save_theme():
    theme=(request.get_json(silent=True) or {}).get('theme')
    if theme not in THEMES:raise ValueError('Choose one of the four themes.')
    new=publish(theme,True)
    if new is None:return jsonify(error='The website changed in another tab. Reload saved content first.'),409
    return jsonify(revision=new['revision'],theme=new['theme'])

@app.post('/api/admin/password')
@admin_required
def change_password():
    body=request.get_json(silent=True) or {};current=body.get('currentPassword','');new=body.get('newPassword','');username=body.get('username','')
    text(current,'Current password',200);text(new,'New password',200);text(username,'Username',60,True)
    if len(new)<12 or new=='Admin@123':raise ValueError('Use a new password with at least 12 characters.')
    if not re.fullmatch(r'[A-Za-z0-9_.@-]{3,60}',username):raise ValueError('Username: 3–60 letters, digits, dots, underscores, @ or hyphens.')
    u=user()
    if not check_password_hash(u['password'],current):return jsonify(error='Current password is incorrect.'),400
    with db() as conn:
        conn.execute('UPDATE users SET username=?,password=?,auth_version=auth_version+1,must_change=0 WHERE id=?',(username,generate_password_hash(new),u['id']))
        audit(conn,'Login credentials updated')
    session['auth_version']=u['auth_version']+1;session['csrf']=secrets.token_urlsafe(32)
    return jsonify(ok=True,username=username,csrf=session['csrf'])

@app.post('/api/admin/upload')
@admin_required
def upload():
    file=request.files.get('image')
    if not file:raise ValueError('Choose an image to upload.')
    raw=file.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:raise ValueError('Choose an image smaller than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ('PNG','JPEG','WEBP') or im.width*im.height>20_000_000:raise ValueError('Use a PNG, JPEG, or WebP image up to 20 megapixels.')
                from PIL import ImageOps
                im=ImageOps.exif_transpose(im);im.thumbnail((2400,2400));im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
                name=secrets.token_hex(16)+'.webp';im.save(UPLOADS/name,'WEBP',quality=90)
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):raise ValueError('This file is not a supported, valid image. Use JPEG, PNG, or WebP.')
    return jsonify(url='/uploads/'+name)

@app.get('/api/admin/backup')
@admin_required
def backup():
    import zipfile
    output=io.BytesIO();doc=document()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('content.json',json.dumps(doc,indent=2))
        seen=set()
        for m in doc['media'].values():
            if m['url'].startswith('/uploads/') and m['url'] not in seen:
                seen.add(m['url'])
                name=m['url'].rsplit('/',1)[1];z.write(UPLOADS/name,'uploads/'+name)
    return Response(output.getvalue(),mimetype='application/zip',headers={'Content-Disposition':'attachment; filename=portfolio-content-backup.zip'})

@app.get('/api/events')
def events():
    # Keep worker capacity for normal pages and admin saves, even when many tabs stay open.
    if not event_slots.acquire(blocking=False):return jsonify(error='Use the revision-check fallback.'),503
    def stream():
        try:
            yield 'retry: 1500\n\n'
            last=None;started=time.time()
            while time.time()-started<45:
                revision=document()['revision']
                if revision!=last:yield 'data: '+json.dumps({'revision':revision})+'\n\n';last=revision
                with condition:condition.wait(timeout=10)
                yield ': keepalive\n\n'
        finally:event_slots.release()
    return Response(stream(),mimetype='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.get('/api/version')
def version():return jsonify(revision=document()['revision'])

@app.get('/uploads/<name>')
def uploaded(name):
    if not re.fullmatch(r'[a-f0-9]{32}\.webp',name):abort(404)
    return send_from_directory(UPLOADS,name,max_age=86400)

@app.get('/assets/<path:name>')
def assets(name):return send_from_directory(ROOT/'assets',name,max_age=86400)

@app.get('/admin')
@app.get('/admin/')
def admin_page():return send_from_directory(ROOT/'admin','index.html')

def themed_css(source):
    theme=THEMES[document()['theme']]
    replacements={'#ff763c':theme['primary'],'#4884ff':theme['secondary'],'#111214':theme['background'],'#191a1d':theme['panel'],'#f1f0ed':theme['text'],'#97989d':theme['muted'], '#1c1d21':theme['panel'],'#18191c':theme['panel'],'#1c1d20':theme['panel'],'#1b1c1f':theme['panel'],'#202125':theme['panel'],'#191b1f':theme['panel'],'#111316':theme['background']}
    for old,new in replacements.items():source=re.sub(re.escape(old),new,source,flags=re.I)
    return source

@app.get('/admin/<name>')
def admin_asset(name):
    if name not in ('admin.js','admin.css'):abort(404)
    if name=='admin.css':return Response(themed_css((ROOT/'admin'/name).read_text()),mimetype='text/css')
    return send_from_directory(ROOT/'admin',name)

@app.get('/health')
def health():
    document();return jsonify(ok=True)

@app.get('/')
def homepage():return page('index.html')

@app.get('/<name>')
def page(name):
    if name in PAGES.values():
        doc=document();key=next(k for k,v in PAGES.items() if v==name)
        state={'revision':doc['revision'],'settings':doc['settings'],'featured':doc['featured']}
        return render_template(name,**{k:doc[k] for k in ('settings','media','services','projects','featured','awards')},texts=doc['pages'][key]['texts'],public_state=state)
    if name.endswith('.css') and (ROOT/name).is_file():
        return Response(themed_css((ROOT/name).read_text()),mimetype='text/css')
    if name in ('script.js','portfolio.js','contact.js','live.js'):return send_from_directory(ROOT,name)
    abort(404)

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='reset-password':
        import getpass
        password=getpass.getpass('New admin password (at least 12 characters): ')
        if len(password)<12:raise SystemExit('Password must be at least 12 characters.')
        with db() as conn:conn.execute('UPDATE users SET password=?,auth_version=auth_version+1,must_change=0',(generate_password_hash(password),))
        print('Password changed; all previous sessions are invalidated.')
    else:app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8080')),debug=False,threaded=True)
