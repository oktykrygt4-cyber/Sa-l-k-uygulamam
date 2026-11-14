"""Kişisel Hekimim 3.0 — PUBLIC DEMO ONLY. Not for real patient data or clinical use."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, sqlite3, threading, webbrowser, os, sys, time, secrets, hashlib, hmac, datetime, http.cookies, base64, binascii

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get('KH_DB_PATH', str(BASE / 'demo.db')))
DB.parent.mkdir(parents=True, exist_ok=True)
PUBLIC_DEMO = os.environ.get('KH_PUBLIC_DEMO', '0') == '1'
PORT = int(os.environ.get('PORT', os.environ.get('KH_PORT', '8765')))
HOST = os.environ.get('KH_HOST', '0.0.0.0' if PUBLIC_DEMO else '127.0.0.1')
SEED = [
 ('V-001','Örnek Hasta A','Diş Hekimliği','Gömülü üçüncü molar','Alerji öyküsü teyit edilmeli.','İlaç öyküsü teyit edilmeli.','demo'),
 ('V-002','Örnek Hasta B','Kardiyoloji','Kardiyak değerlendirme','Alerji durumu bilinmiyor.','İlaç listesi doğrulanmalı.','demo'),
 ('V-003','Örnek Hasta C','Ortodonti','Dişlenme gelişimi','Alerji öyküsü bilinmiyor.','Düzenli ilaç bildirilmedi.','demo'),
]
def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,180000)
    return salt.hex()+':'+digest.hex()

def verify_password(password, encoded):
    try:
        salt, digest=encoded.split(':',1)
        got=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),180000)
        return hmac.compare_digest(got,bytes.fromhex(digest))
    except (ValueError,AttributeError): return False

def connect():
    db=sqlite3.connect(DB, timeout=10)
    db.row_factory=sqlite3.Row
    return db

def setup():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, patient TEXT NOT NULL, specialty TEXT NOT NULL, subject TEXT NOT NULL, history TEXT, medications TEXT, status TEXT NOT NULL DEFAULT \'demo\')')
        db.execute("CREATE TABLE IF NOT EXISTS case_details (case_id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, age TEXT NOT NULL DEFAULT '', complaint TEXT NOT NULL DEFAULT '', assessment_type TEXT NOT NULL DEFAULT 'surgery', question TEXT NOT NULL DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(id), body TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute('CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, expert TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'taslak\', created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute('CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, person TEXT NOT NULL, date TEXT NOT NULL, type TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'bekliyor\')')
        db.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, specialty TEXT NOT NULL, email TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'doğrulanmadı\')')
        db.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, body TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL, profession TEXT NOT NULL, specialty TEXT NOT NULL, city TEXT, school TEXT, institution TEXT, biography TEXT, publications TEXT, accepting INTEGER NOT NULL DEFAULT 0, visibility TEXT NOT NULL DEFAULT 'private')")
        db.execute("CREATE TABLE IF NOT EXISTS clinical_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL REFERENCES requests(id), findings TEXT NOT NULL DEFAULT '', assessment TEXT NOT NULL DEFAULT '', options TEXT NOT NULL DEFAULT '', risks TEXT NOT NULL DEFAULT '', literature TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'taslak', updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_report_request ON clinical_reports(request_id)')
        db.execute("CREATE TABLE IF NOT EXISTS case_plans (case_id TEXT NOT NULL REFERENCES cases(id), scenario TEXT NOT NULL CHECK(scenario IN ('A','B','C')), plan_note TEXT NOT NULL DEFAULT '', PRIMARY KEY(case_id,scenario))")
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL CHECK(role IN ('patient','doctor')), full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL)')
        db.execute("CREATE TABLE IF NOT EXISTS patient_records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL, role TEXT NOT NULL, case_id TEXT DEFAULT '', filename TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, data BLOB NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, title TEXT DEFAULT '', profession TEXT DEFAULT '', specialty TEXT DEFAULT '', city TEXT DEFAULT '', institution TEXT DEFAULT '', school TEXT DEFAULT '', experience TEXT DEFAULT '', biography TEXT DEFAULT '', publications TEXT DEFAULT '', phone TEXT DEFAULT '', birth_date TEXT DEFAULT '', accepting INTEGER DEFAULT 0, visibility TEXT DEFAULT 'private', notify INTEGER DEFAULT 1, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS doctor_schedule (user_id INTEGER PRIMARY KEY, days TEXT NOT NULL DEFAULT '0,1,2,3,4', start_time TEXT NOT NULL DEFAULT '09:00', end_time TEXT NOT NULL DEFAULT '17:00', duration INTEGER NOT NULL DEFAULT 30, visit_type TEXT NOT NULL DEFAULT 'both', auto_confirm INTEGER NOT NULL DEFAULT 0)")
        db.execute("CREATE TABLE IF NOT EXISTS peer_consults (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL, subject TEXT NOT NULL, question TEXT NOT NULL, response TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        for col,typ in [('consult_type',"TEXT NOT NULL DEFAULT 'written'"),('case_ref',"TEXT NOT NULL DEFAULT ''")]:
            if col not in [r['name'] for r in db.execute('PRAGMA table_info(peer_consults)')]:
                db.execute('ALTER TABLE peer_consults ADD COLUMN '+col+' '+typ)
        db.execute("CREATE TABLE IF NOT EXISTS connections (id INTEGER PRIMARY KEY AUTOINCREMENT, requester_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(requester_id,recipient_id))")
        db.execute("CREATE TABLE IF NOT EXISTS doctor_inbox (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_id INTEGER NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', read INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS patient_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL, specialty TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'bekliyor', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        for table,col,sqltype in [('cases','owner_id','INTEGER'),('notes','owner_id','INTEGER'),('requests','owner_id','INTEGER'),('appointments','owner_id','INTEGER'),('contacts','owner_id','INTEGER'),('messages','owner_id','INTEGER'),('patient_requests','doctor_id','INTEGER')]:
            if col not in [r['name'] for r in db.execute('PRAGMA table_info('+table+')')]:
                db.execute('ALTER TABLE '+table+' ADD COLUMN '+col+' '+sqltype)
        for role, name, email in [('patient','Örnek Hasta','hasta@demo.local'),('doctor','Örnek Hekim','hekim@demo.local')]:
            if not db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
                db.execute('INSERT INTO users(role,full_name,email,password_hash) VALUES(?,?,?,?)',(role,name,email,hash_password('Demo12345!')))
        # Kurgusal, yerel test profilleri: gerçek hekim veya doğrulanmış kimlik değildir.
        sample_doctors=[('Demo Dr. Ayşe Demir (Kurgusal)','demo.ayse@local.test','Ağız, Diş ve Çene Cerrahisi','İstanbul'),
                        ('Demo Dr. Mert Aksoy (Kurgusal)','demo.mert@local.test','Radyoloji','Ankara'),
                        ('Demo Dr. Selin Kaya (Kurgusal)','demo.selin@local.test','Ortodonti','İstanbul')]
        for name,email,specialty,city in sample_doctors:
            if not db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
                db.execute('INSERT INTO users(role,full_name,email,password_hash) VALUES(?,?,?,?)',('doctor',name,email,hash_password('Demo12345!')))
            uid=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
            db.execute("INSERT OR IGNORE INTO user_profiles(user_id,title,profession,specialty,city,institution,biography,accepting,visibility) VALUES(?,?,?,?,?,?,?,?,?)",(uid,'Dr.','Tıp' if specialty=='Radyoloji' else 'Diş Hekimliği',specialty,city,'Kurgusal Demo Kurumu','Yalnızca yazılım işlevlerini denemek için oluşturulmuş kurgusal hekim profili.',1,'verified'))
        for row in db.execute('SELECT id,role,full_name FROM users').fetchall():
            if not db.execute('SELECT 1 FROM user_profiles WHERE user_id=?',(row['id'],)).fetchone():
                db.execute('INSERT INTO user_profiles(user_id,title,profession,biography) VALUES(?,?,?,?)',(row['id'],'Dr.' if row['role']=='doctor' else '','Tıp' if row['role']=='doctor' else '',''))
        for row in db.execute("SELECT id FROM users WHERE role='doctor'").fetchall():
            db.execute('INSERT OR IGNORE INTO doctor_schedule(user_id) VALUES(?)',(row['id'],))
        demo_doc=db.execute("SELECT id FROM users WHERE email='hekim@demo.local'").fetchone()
        if demo_doc:
            for t in ('cases','notes','requests','appointments','contacts','messages'):
                db.execute('UPDATE '+t+' SET owner_id=? WHERE owner_id IS NULL',(demo_doc['id'],))
            db.execute('UPDATE patient_requests SET doctor_id=? WHERE doctor_id IS NULL',(demo_doc['id'],))
        if not db.execute('SELECT 1 FROM profile WHERE id=1').fetchone():
            db.execute('INSERT INTO profile (id,name,profession,specialty,city,school,institution,biography,publications,accepting,visibility) VALUES (1,?,?,?,?,?,?,?,?,?,?)',('Dr. Örnek Hekim','Diş Hekimliği','Genel Diş Hekimliği','İstanbul','','','','',0,'private'))
        if db.execute('SELECT count(*) FROM cases').fetchone()[0] == 0:
            db.executemany('INSERT INTO cases(id,patient,specialty,subject,history,medications,status,owner_id) VALUES (?,?,?,?,?,?,?,?)', [(*r,demo_doc['id']) for r in SEED])
        if db.execute('SELECT count(*) FROM appointments').fetchone()[0] == 0:
            db.executemany('INSERT INTO appointments(person,date,type,status,owner_id) VALUES (?,?,?,?,?)',[('Örnek Hasta A','2026-11-16 10:00','Yüz yüze','onaylandı',demo_doc['id']),('Örnek Hasta B','2026-11-17 11:30','Çevrim içi','bekliyor',demo_doc['id']),('Örnek Hekim C','2026-11-17 14:00','Konsültasyon','onaylandı',demo_doc['id'])])
        if db.execute('SELECT count(*) FROM contacts').fetchone()[0] == 0:
            db.executemany('INSERT INTO contacts(name,specialty,email,status,owner_id) VALUES (?,?,?,?,?)',[('Dr. Deniz Yılmaz','Ağız, Diş ve Çene Cerrahisi','deniz@example.invalid','örnek',demo_doc['id']),('Dr. Selin Arslan','Kardiyoloji','selin@example.invalid','örnek',demo_doc['id'])])

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(BASE / 'static'),**kw)
    def session_user(self):
        jar=http.cookies.SimpleCookie()
        try: jar.load(self.headers.get('Cookie',''))
        except http.cookies.CookieError: return None
        if 'kh_session' not in jar:return None
        token=jar['kh_session'].value
        digest=hashlib.sha256(token.encode()).hexdigest()
        with connect() as db:
            row=db.execute('SELECT u.id,u.role,u.full_name,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(digest,int(time.time()))).fetchone()
            return dict(row) if row else None
    def send_auth_cookie(self,token,delete=False):
        c=http.cookies.SimpleCookie()
        c['kh_session']=token
        c['kh_session']['httponly']=True
        if PUBLIC_DEMO: c['kh_session']['secure']=True
        c['kh_session']['samesite']='Strict'
        c['kh_session']['path']='/'
        if delete:c['kh_session']['max-age']=0
        self.send_header('Set-Cookie',c.output(header='').strip())
    def end_headers(self):
        self.send_header('Cache-Control','no-store, max-age=0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        if PUBLIC_DEMO: self.send_header('X-Robots-Tag','noindex, nofollow')
        super().end_headers()
    def send_json(self,data,status=200,auth_cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(raw))); 
        if auth_cookie is not None:self.send_auth_cookie(auth_cookie,auth_cookie=='')
        self.end_headers(); self.wfile.write(raw)
    def read_json(self,max_bytes=200000):
        size=int(self.headers.get('Content-Length','0'))
        if size<1 or size>max_bytes: raise ValueError('İstek boyutu geçersiz')
        data=json.loads(self.rfile.read(size))
        if not isinstance(data,dict): raise ValueError('Geçersiz veri')
        return data
    def do_GET(self):
        path=urlparse(self.path).path
        if path == '/api/auth/me': return self.send_json({'user':self.session_user()})
        if path.startswith('/api/attachment/'):
            user=self.session_user()
            if not user:return self.send_json({'error':'Giriş gerekli'},401)
            try: fid=int(path.rsplit('/',1)[1])
            except ValueError:return self.send_json({'error':'Geçersiz dosya'},400)
            with connect() as db:
                r=db.execute('SELECT mime,filename,size,data FROM attachments WHERE id=? AND owner_id=?',(fid,user['id'])).fetchone()
                if not r:return self.send_json({'error':'Dosya bulunamadı'},404)
                self.send_response(200);self.send_header('Content-Type',r['mime']);self.send_header('Content-Disposition','inline; filename="'+''.join(c for c in r['filename'] if c.isascii() and (c.isalnum() or c in '._-'))[:120]+'"');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(r['size']));self.end_headers();self.wfile.write(r['data']);return
        if path == '/api/user/profile':
            user=self.session_user()
            if not user:return self.send_json({'error':'Giriş gerekli'},401)
            with connect() as db:
                r=db.execute('SELECT * FROM user_profiles WHERE user_id=?',(user['id'],)).fetchone()
                return self.send_json({'user':user,'profile':dict(r) if r else {}})
        if path == '/api/schedule':
            user=self.session_user()
            if not user:return self.send_json({'error':'Giriş gerekli'},401)
            with connect() as db:
                if user['role']=='doctor':
                    r=db.execute('SELECT * FROM doctor_schedule WHERE user_id=?',(user['id'],)).fetchone()
                    return self.send_json({'schedule':dict(r) if r else {}})
                return self.send_json({'schedule':{}})
        if path == '/api/patient/doctors':
            user=self.session_user()
            if not user or user['role']!='patient':return self.send_json({'error':'Yetkisiz'},403)
            with connect() as db:
                rows=[dict(r) for r in db.execute("SELECT u.id,u.full_name,p.title,p.specialty,p.city,p.accepting,s.days,s.start_time,s.end_time,s.duration,s.visit_type FROM users u JOIN user_profiles p ON u.id=p.user_id LEFT JOIN doctor_schedule s ON s.user_id=u.id WHERE u.role='doctor' AND p.visibility='verified' AND p.accepting=1 ORDER BY u.full_name")]
                return self.send_json({'doctors':rows})
        if path == '/api/peer-consults':
            user=self.session_user()
            if not user or user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
            with connect() as db:
                rows=[dict(r) for r in db.execute('SELECT pc.*,a.full_name AS sender_name,b.full_name AS recipient_name FROM peer_consults pc JOIN users a ON a.id=pc.sender_id JOIN users b ON b.id=pc.recipient_id WHERE pc.sender_id=? OR pc.recipient_id=? ORDER BY pc.id DESC',(user['id'],user['id']))]
                return self.send_json({'consults':rows,'self_id':user['id']})
        if path == '/api/network':
            user=self.session_user()
            if not user or user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
            with connect() as db:
                doctors=[dict(r) for r in db.execute("SELECT u.id,u.full_name,p.title,p.specialty,p.profession,p.city,p.institution,p.biography,p.accepting,p.visibility FROM users u JOIN user_profiles p ON u.id=p.user_id WHERE u.role='doctor' AND u.id!=? AND p.visibility='verified' ORDER BY u.full_name",(user['id'],))]
                connections=[dict(r) for r in db.execute('SELECT c.*,u.full_name AS requester_name,v.full_name AS recipient_name FROM connections c JOIN users u ON u.id=c.requester_id JOIN users v ON v.id=c.recipient_id WHERE c.requester_id=? OR c.recipient_id=? ORDER BY c.id DESC',(user['id'],user['id']))]
                return self.send_json({'doctors':doctors,'connections':connections,'self_id':user['id']})
        if path == '/api/health': return self.send_json({'status':'ok','mode':'public_demo' if PUBLIC_DEMO else 'local_demo_unified'})
        if path.startswith('/api/'):
            user=self.session_user()
            if not user:return self.send_json({'error':'Giriş gerekli'},401)
            if path=='/api/attachments':
                with connect() as db:
                    rows=[dict(r) for r in db.execute('SELECT id,filename,mime,size,case_id,created_at FROM attachments WHERE owner_id=? ORDER BY id DESC',(user['id'],))]
                    return self.send_json({'files':rows})
            if path=='/api/patient/state':
                if user['role']!='patient':return self.send_json({'error':'Yetkisiz'},403)
                with connect() as db:
                    records=[dict(r) for r in db.execute('SELECT * FROM patient_records WHERE user_id=? ORDER BY id DESC',(user['id'],))]
                    requests=[dict(r) for r in db.execute('SELECT * FROM patient_requests WHERE user_id=? ORDER BY id DESC',(user['id'],))]
                    return self.send_json({'records':records,'requests':requests,'user':user})
            if path == '/api/state':
                if user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
                with connect() as db:
                    names=['cases','notes','requests','appointments','contacts','messages','clinical_reports','case_plans']
                    payload={n:[dict(row) for row in db.execute('SELECT * FROM '+n+' WHERE owner_id=? ORDER BY rowid DESC',(user['id'],))] for n in names if n not in ('clinical_reports','case_plans')}
                    payload['clinical_reports']=[dict(row) for row in db.execute('SELECT r.* FROM clinical_reports r JOIN requests q ON q.id=r.request_id WHERE q.owner_id=? ORDER BY r.id DESC',(user['id'],))]
                    payload['case_plans']=[dict(row) for row in db.execute('SELECT p.* FROM case_plans p JOIN cases c ON c.id=p.case_id WHERE c.owner_id=?',(user['id'],))]
                    payload['case_details']=[dict(row) for row in db.execute('SELECT * FROM case_details WHERE owner_id=?',(user['id'],))]
                    payload['schedule']=dict(db.execute('SELECT * FROM doctor_schedule WHERE user_id=?',(user['id'],)).fetchone() or {})
                    payload['profile']=dict(db.execute('SELECT * FROM user_profiles WHERE user_id=?',(user['id'],)).fetchone()); payload['user']=user
                    payload['patient_requests']=[dict(row) for row in db.execute('SELECT pr.id,pr.kind,pr.specialty,pr.message,pr.status,pr.created_at,u.full_name AS patient_name FROM patient_requests pr JOIN users u ON u.id=pr.user_id WHERE pr.doctor_id=? ORDER BY pr.id DESC',(user['id'],))]
                    return self.send_json(payload)
            return self.send_json({'error':'Yol bulunamadı'},404)
        if path in ('/doctor.html','/patient.html'):
            user=self.session_user()
            expected='doctor' if path=='/doctor.html' else 'patient'
            if not user or user['role']!=expected:
                self.send_response(302);self.send_header('Location','/');self.end_headers();return
        return super().do_GET()
    def do_POST(self):
        # Same-origin enforcement. HTTPS termination is handled by the hosting provider.
        origin=self.headers.get('Origin','')
        if PUBLIC_DEMO:
            expected_host=self.headers.get('Host','')
            expected_origin='https://'+expected_host
            if not origin or origin.rstrip('/')!=expected_origin:
                return self.send_json({'error':'Geçersiz isteğin kaynağı'},403)
        elif origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.send_json({'error':'Bu kaynak için erişim yok'},403)

        path=urlparse(self.path).path
        if path.startswith('/api/auth/'):
            try:
                d=self.read_json()
                if path=='/api/auth/logout':
                    jar=http.cookies.SimpleCookie();jar.load(self.headers.get('Cookie',''))
                    if 'kh_session' in jar:
                        with connect() as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(jar['kh_session'].value.encode()).hexdigest(),))
                    return self.send_json({'ok':True},auth_cookie='')
                if path not in ('/api/auth/login','/api/auth/register'):return self.send_json({'error':'Yol bulunamadı'},404)
                if PUBLIC_DEMO and path == '/api/auth/register': return self.send_json({'error':'Çevrim içi test sürümünde yeni hesap açma kapalıdır. Örnek hesapları kullanın.'},403)
                email=str(d.get('email','')).strip().lower()
                password=d.get('password','')
                if not isinstance(password,str) or not email or len(email)>180 or '@' not in email:return self.send_json({'error':'E-posta / parola geçersiz'},400)
                with connect() as db:
                    if path.endswith('register'):
                        name=str(d.get('full_name','')).strip()[:120];role=d.get('role')
                        if role not in ('doctor','patient') or not name or len(password)<8:return self.send_json({'error':'Ad, rol ve en az 8 karakterli parola gerekli'},400)
                        if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():return self.send_json({'error':'Bu e-posta kullanılıyor'},409)
                        db.execute('INSERT INTO users(role,full_name,email,password_hash) VALUES(?,?,?,?)',(role,name,email,hash_password(password)))
                        uid=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
                        db.execute('INSERT INTO user_profiles(user_id,title,profession,specialty,phone,birth_date) VALUES(?,?,?,?,?,?)',(uid,str(d.get('title',''))[:60],str(d.get('profession',''))[:80],str(d.get('specialty',''))[:140],str(d.get('phone',''))[:40],str(d.get('birth_date',''))[:30]))
                        if role=='doctor':db.execute('INSERT OR IGNORE INTO doctor_schedule(user_id) VALUES(?)',(uid,))
                    row=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                    if not row or not verify_password(password,row['password_hash']):return self.send_json({'error':'E-posta veya parola hatalı'},401)
                    token=secrets.token_urlsafe(36)
                    db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],int(time.time())+8*3600))
                    return self.send_json({'ok':True,'role':row['role']},auth_cookie=token)
            except (ValueError,TypeError,sqlite3.Error) as ex:return self.send_json({'error':str(ex)},400)
        user=self.session_user()
        if not user:return self.send_json({'error':'Giriş gerekli'},401)
        if path in ('/api/schedule','/api/peer-consults/new','/api/peer-consults/respond','/api/peer-consults/reply','/api/attachments','/api/user/profile','/api/user/password','/api/network/connect','/api/network/respond'):
            if PUBLIC_DEMO and path in ('/api/attachments','/api/user/password'):
                return self.send_json({'error':'Kamuya açık demoda dosya yükleme ve parola değişimi kapalıdır.'},403)
            try:
                d=self.read_json(max_bytes=8500000 if path=='/api/attachments' else 200000)
                with connect() as db:
                    if path=='/api/schedule':
                        if user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
                        days=d.get('days');start=d.get('start_time');end=d.get('end_time');duration=d.get('duration');visit=d.get('visit_type');auto=1 if d.get('auto_confirm') else 0
                        if not isinstance(days,list) or any(not isinstance(x,int) or x not in range(7) for x in days) or len(days)>7:raise ValueError('Gün seçimi geçersiz')
                        import re
                        if not isinstance(start,str) or not isinstance(end,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',start) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',end) or start>=end:raise ValueError('Çalışma saatleri geçersiz')
                        if duration not in (15,30,45,60) or visit not in ('both','physical','online'):raise ValueError('Görüşme ayarı geçersiz')
                        db.execute('INSERT INTO doctor_schedule(user_id,days,start_time,end_time,duration,visit_type,auto_confirm) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET days=excluded.days,start_time=excluded.start_time,end_time=excluded.end_time,duration=excluded.duration,visit_type=excluded.visit_type,auto_confirm=excluded.auto_confirm',(user['id'],','.join(map(str,sorted(set(days)))),start,end,duration,visit,auto))
                    elif path.startswith('/api/peer-consults/'):
                        if user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
                        if path.endswith('/new'):
                            recipient=int(d.get('recipient_id',0));subject=str(d.get('subject','')).strip()[:160];question=str(d.get('question','')).strip()[:3000];consult_type=d.get('consult_type','written');case_ref=str(d.get('case_ref','')).strip()[:64]
                            if not subject or len(question)<5 or user['id']==recipient or consult_type not in ('written','video'):raise ValueError('Konsültasyon bilgileri eksik')
                            if case_ref and not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case_ref,user['id'])).fetchone():raise ValueError('Vaka referansı geçersiz')
                            if not db.execute("SELECT 1 FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE u.id=? AND u.role='doctor' AND p.accepting=1 AND p.visibility='verified'",(recipient,)).fetchone():raise ValueError('Hekim konsültasyon almıyor')
                            db.execute('INSERT INTO peer_consults(sender_id,recipient_id,subject,question,consult_type,case_ref) VALUES(?,?,?,?,?,?)',(user['id'],recipient,subject,question,consult_type,case_ref))
                        elif path.endswith('/respond'):
                            id=int(d.get('id',0));status=d.get('status')
                            if status not in ('accepted','rejected'):raise ValueError('Geçersiz karar')
                            cur=db.execute("UPDATE peer_consults SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND recipient_id=? AND status='pending'",(status,id,user['id']))
                            if cur.rowcount!=1:raise ValueError('Talep bulunamadı')
                        else:
                            id=int(d.get('id',0));response=d.get('response','')
                            if not isinstance(response,str) or not response.strip() or len(response)>4000:raise ValueError('Görüş metni geçersiz')
                            cur=db.execute("UPDATE peer_consults SET response=?,status='replied',updated_at=CURRENT_TIMESTAMP WHERE id=? AND recipient_id=? AND status='accepted'",(response.strip(),id,user['id']))
                            if cur.rowcount!=1:raise ValueError('Kabul edilmiş talep bulunamadı')
                    elif path=='/api/attachments':
                        name=d.get('filename','');mime=d.get('mime','');encoded=d.get('base64','');case_id=d.get('case_id','')
                        allowed=('application/pdf','image/png','image/jpeg','application/dicom')
                        if not isinstance(name,str) or not isinstance(mime,str) or not isinstance(encoded,str) or not isinstance(case_id,str) or mime not in allowed:raise ValueError('Desteklenmeyen dosya türü')
                        if not 1<len(name)<200 or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise ValueError('Dosya adı geçersiz')
                        try:data=base64.b64decode(encoded,validate=True)
                        except (ValueError,binascii.Error):raise ValueError('Dosya kodlaması geçersiz')
                        if not data or len(data)>6000000:raise ValueError('Dosya 6 MB sınırını aşıyor')
                        if mime=='application/pdf' and not data.startswith(b'%PDF-'):raise ValueError('PDF biçimi geçersiz')
                        if mime=='image/png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('PNG biçimi geçersiz')
                        if mime=='image/jpeg' and not data.startswith(b'\xff\xd8\xff'):raise ValueError('JPEG biçimi geçersiz')
                        if user['role']=='doctor':
                            if not case_id or not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case_id,user['id'])).fetchone():raise ValueError('Yetkili vaka seçilmeli')
                        else:case_id=''
                        db.execute('INSERT INTO attachments(owner_id,role,case_id,filename,mime,size,data) VALUES(?,?,?,?,?,?,?)',(user['id'],user['role'],case_id,name,mime,len(data),data))
                    elif path=='/api/user/profile':
                        allowed=['title','profession','specialty','city','institution','school','experience','biography','publications','phone','birth_date','visibility']
                        values=[]
                        for k in allowed:
                            v=d.get(k,'')
                            if not isinstance(v,str):raise ValueError('Geçersiz alan: '+k)
                            values.append(v.strip()[:2000 if k in ('biography','publications','experience') else 200])
                        if values[-1] not in ('private','connections','verified'):raise ValueError('Görünürlük geçersiz')
                        full_name=d.get('full_name')
                        if full_name is not None:
                            if not isinstance(full_name,str) or not full_name.strip() or len(full_name)>120:raise ValueError('Ad soyad geçersiz')
                            db.execute('UPDATE users SET full_name=? WHERE id=?',(full_name.strip(),user['id']))
                        accepting=1 if d.get('accepting') else 0;notify=1 if d.get('notify',True) else 0
                        db.execute('INSERT OR IGNORE INTO user_profiles(user_id) VALUES(?)',(user['id'],))
                        db.execute('UPDATE user_profiles SET '+','.join(k+'=?' for k in allowed)+',accepting=?,notify=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?',(*values,accepting,notify,user['id']))
                    elif path=='/api/user/password':
                        old=d.get('current','');new=d.get('new','')
                        if not isinstance(old,str) or not isinstance(new,str) or len(new)<8 or len(new)>128:raise ValueError('Yeni parola 8–128 karakter olmalı')
                        pw=db.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()['password_hash']
                        if not verify_password(old,pw):raise ValueError('Mevcut parola yanlış')
                        db.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new),user['id']))
                        db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
                        return self.send_json({'ok':True,'relogin':True},auth_cookie='')
                    else:
                        if user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
                        if path.endswith('connect'):
                            target=int(d.get('doctor_id',0))
                            if target==user['id'] or not db.execute("SELECT 1 FROM users WHERE id=? AND role='doctor'",(target,)).fetchone():raise ValueError('Hekim bulunamadı')
                            db.execute('INSERT OR IGNORE INTO connections(requester_id,recipient_id) VALUES(?,?)',(user['id'],target))
                        else:
                            target=int(d.get('id',0));status=d.get('status')
                            if status not in ('accepted','rejected'):raise ValueError('Geçersiz yanıt')
                            db.execute("UPDATE connections SET status=? WHERE id=? AND recipient_id=? AND status='pending'",(status,target,user['id']))
                return self.send_json({'ok':True})
            except (ValueError,TypeError,sqlite3.Error) as ex:return self.send_json({'error':str(ex)},400)
        if path in ('/api/patient/records','/api/patient/requests'):
            if user['role']!='patient':return self.send_json({'error':'Yetkisiz'},403)
            try:
                d=self.read_json()
                def value(k,n=2500):
                    v=d.get(k,'')
                    if not isinstance(v,str):raise ValueError('Geçersiz alan')
                    return v.strip()[:n]
                with connect() as db:
                    if path.endswith('records'):
                        kind=value('kind',60);title=value('title',200);body=value('body')
                        if kind not in ('chat','checkup','health','lab','document') or not title or not body:raise ValueError('Eksik bilgi')
                        db.execute('INSERT INTO patient_records(user_id,kind,title,body) VALUES(?,?,?,?)',(user['id'],kind,title,body))
                    else:
                        kind=value('kind',60);field=value('specialty',100);msg=value('message')
                        if kind not in ('opinion','appointment') or not field or not msg:raise ValueError('Eksik talep')
                        target=int(d.get('doctor_id',0) or 0)
                        if target:
                            ok=db.execute("SELECT 1 FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE u.id=? AND u.role='doctor' AND p.accepting=1 AND p.visibility='verified'",(target,)).fetchone()
                            if not ok:raise ValueError('Seçilen hekim uygun değil')
                        else:
                            demo=db.execute("SELECT id FROM users WHERE email='hekim@demo.local'").fetchone();target=demo['id'] if demo else 0
                        if not target:raise ValueError('Talep gönderilecek hekim bulunamadı')
                        db.execute('INSERT INTO patient_requests(user_id,kind,specialty,message,doctor_id) VALUES(?,?,?,?,?)',(user['id'],kind,field,msg,target))
                return self.send_json({'ok':True})
            except (ValueError,sqlite3.Error) as ex:return self.send_json({'error':str(ex)},400)
        if user['role']!='doctor':return self.send_json({'error':'Yetkisiz'},403)
        try:
            d=self.read_json()
            def val(k,limit=2000):
                s=d.get(k,'')
                if not isinstance(s,str): raise ValueError('Geçersiz alan: '+k)
                return s.strip()[:limit]
            with connect() as db:
                if path=='/api/patient-request-status':
                    status=val('status',20)
                    if status not in ('inceleniyor','yanıtlandı','reddedildi'): raise ValueError('Durum geçersiz')
                    db.execute('UPDATE patient_requests SET status=? WHERE id=? AND doctor_id=?',(status,int(d['id']),user['id']))
                elif path=='/api/legacy-profile-disabled':
                    visibility=val('visibility',20)
                    if visibility not in ('private','connections','verified'): raise ValueError('Görünürlük geçersiz')
                    name=val('name',120)
                    if not name: raise ValueError('İsim gerekli')
                    db.execute('UPDATE profile SET name=?,profession=?,specialty=?,city=?,school=?,institution=?,biography=?,publications=?,accepting=?,visibility=? WHERE id=1',
                       (name,val('profession',80),val('specialty',120),val('city',80),val('school',250),val('institution',250),val('biography'),val('publications'),int(d.get('accepting')=='on'),visibility))
                elif path=='/api/report':
                    reqid=int(d.get('request_id'))
                    if not db.execute('SELECT 1 FROM requests WHERE id=? AND owner_id=?',(reqid,user['id'])).fetchone(): raise ValueError('Konsültasyon taslağı bulunamadı')
                    status=val('status',20)
                    if status!='taslak': raise ValueError('Bu sürümde yalnızca rapor taslağı kaydedilebilir')
                    values=[val('findings'),val('assessment'),val('options'),val('risks'),val('literature')]
                    db.execute('INSERT INTO clinical_reports(request_id,findings,assessment,options,risks,literature,status) VALUES(?,?,?,?,?,?,?) ON CONFLICT(request_id) DO UPDATE SET findings=excluded.findings,assessment=excluded.assessment,options=excluded.options,risks=excluded.risks,literature=excluded.literature,updated_at=CURRENT_TIMESTAMP', (reqid,*values,status))
                elif path=='/api/plan':
                    case=val('case_id',80); scenario=val('scenario',1)
                    if scenario not in ('A','B','C'): raise ValueError('Senaryo geçersiz')
                    if not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case,user['id'])).fetchone(): raise ValueError('Vaka bulunamadı')
                    db.execute('INSERT INTO case_plans(case_id,scenario,plan_note) VALUES(?,?,?) ON CONFLICT(case_id,scenario) DO UPDATE SET plan_note=excluded.plan_note',(case,scenario,val('plan_note')))
                elif path=='/api/cases':
                    patient, specialty, subject=val('patient',120),val('specialty',100),val('subject',150)
                    if not patient or not subject: raise ValueError('Hasta kodu ve vaka konusu gerekli')
                    i='V-'+str(time.time_ns())
                    db.execute('INSERT INTO cases(id,patient,specialty,subject,history,medications,status,owner_id) VALUES(?,?,?,?,?,?,?,?)',(i,patient,specialty,subject,val('history'),val('medications'),'demo',user['id']))
                    db.execute('INSERT INTO case_details(case_id,owner_id,age,complaint,assessment_type,question) VALUES(?,?,?,?,?,?)',(i,user['id'],val('age',12),val('complaint',3000),val('assessment_type',80),val('question',3000)))
                elif path=='/api/case-update':
                    case=val('case_id',80)
                    if not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case,user['id'])).fetchone(): raise ValueError('Yetkisiz veya bulunamayan vaka')
                    db.execute('UPDATE cases SET patient=?,specialty=?,subject=?,history=?,medications=? WHERE id=? AND owner_id=?',(val('patient',120),val('specialty',100),val('subject',150),val('history',3000),val('medications',3000),case,user['id']))
                    db.execute('INSERT INTO case_details(case_id,owner_id,age,complaint,assessment_type,question) VALUES(?,?,?,?,?,?) ON CONFLICT(case_id) DO UPDATE SET age=excluded.age,complaint=excluded.complaint,assessment_type=excluded.assessment_type,question=excluded.question,updated_at=CURRENT_TIMESTAMP',(case,user['id'],val('age',12),val('complaint',3000),val('assessment_type',80),val('question',3000)))
                elif path=='/api/notes':
                    case,body=val('case_id',80),val('body')
                    if not case or not body: raise ValueError('Eksik not')
                    if not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case,user['id'])).fetchone(): raise ValueError('Vaka bulunamadı')
                    db.execute('INSERT INTO notes(case_id,body,owner_id) VALUES(?,?,?)',(case,body,user['id']))
                elif path=='/api/requests':
                    case,expert,question=val('case_id',80),val('expert',120),val('question')
                    if not all([case,expert,question]): raise ValueError('Eksik konsültasyon taslağı')
                    if not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case,user['id'])).fetchone(): raise ValueError('Vaka bulunamadı')
                    db.execute('INSERT INTO requests(case_id,expert,question,owner_id) VALUES(?,?,?,?)',(case,expert,question,user['id']))
                elif path=='/api/appointments':
                    person,date,typ=val('person',120),val('date',40),val('type',100)
                    if not all([person,date,typ]): raise ValueError('Eksik randevu')
                    db.execute('INSERT INTO appointments(person,date,type,owner_id) VALUES (?,?,?,?)',(person,date,typ,user['id']))
                elif path=='/api/contacts':
                    name,field,email=val('name',120),val('specialty',120),val('email',160)
                    if not name or not field or '@' not in email: raise ValueError('Hekim adı, uzmanlık ve e-posta gerekli')
                    db.execute('INSERT INTO contacts(name,specialty,email) VALUES (?,?,?)',(name,field,email))
                elif path=='/api/messages':
                    case,body=val('case_id',80),val('body')
                    if not body or not case: raise ValueError('Eksik mesaj')
                    if not db.execute('SELECT 1 FROM cases WHERE id=? AND owner_id=?',(case,user['id'])).fetchone():raise ValueError('Yetkisiz vaka')
                    db.execute('INSERT INTO messages(case_id,body,role,owner_id) VALUES(?,?,\'user\',?)',(case,body,user['id']))
                    db.execute("INSERT INTO messages(case_id,body,role,owner_id) VALUES(?,?,'assistant',?)",(case,'Bu yerel prototip gerçek klinik analiz yapmaz. Hasta özelinde tıbbi öneri veya kaynak değerlendirmesi üretilmemiştir.',user['id']))
                elif path=='/api/appointment-status':
                    status=val('status',30)
                    if status not in ('onaylandı','reddedildi'): raise ValueError('Durum geçersiz')
                    db.execute('UPDATE appointments SET status=? WHERE id=? AND owner_id=?',(status,int(d['id']),user['id']))
                else: return self.send_json({'error':'Yol bulunamadı'},404)
            self.send_json({'ok':True})
        except (ValueError,KeyError,TypeError,sqlite3.Error,json.JSONDecodeError) as ex:
            self.send_json({'error':str(ex)},400)
    def log_message(self,fmt,*args):
        # Never log request bodies, passwords, authorization headers or query strings.
        import datetime
        import re
        message=(fmt % args) if args else fmt
        message=re.sub(r'([?][^ ]+)', '?...', message)
        stamp=datetime.datetime.now().strftime('%H:%M:%S')
        print(f'[{stamp}] {message}', flush=True)

def main():
    print('='*57, flush=True)
    print('  KİŞİSEL HEKİMİM 3.0  |  ' + ('PUBLIC DEMO' if PUBLIC_DEMO else 'YEREL UYGULAMA'), flush=True)
    print('='*57, flush=True)
    print('[1/4] Python sunucusu başlatılıyor...', flush=True)
    try:
        setup()
        print('[2/4] Veritabanı kontrolü: BAŞARILI', flush=True)
    except Exception as exc:
        print('[HATA] Veritabanı başlatılamadı:', exc, flush=True)
        raise
    server=None
    candidates=[PORT] if PUBLIC_DEMO else [PORT, 8766, 8767, 8768, 0]
    for candidate in candidates:
        try:
            server=ThreadingHTTPServer((HOST,candidate),Handler)
            break
        except OSError:
            continue
    if server is None:
        print('[HATA] Sunucu başlatılamadı.', flush=True)
        sys.exit(1)
    url=f'http://127.0.0.1:{server.server_port}'
    print('[3/4] Sunucu hazır: '+url, flush=True)
    print('Bu sürüm yalnızca kurgusal verilerle kullanım içindir.', flush=True)
    if not PUBLIC_DEMO:
        print('[4/4] Tarayıcı açılıyor...', flush=True)
        threading.Timer(0.8,lambda:webbrowser.open(url)).start()
    else:
        print('[4/4] Bulut sunucusunda tarayıcı otomatik açılmaz.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: print('\n[ÇIKIŞ] Sunucu kullanıcı tarafından durduruldu.', flush=True)
    finally:
        server.server_close()
if __name__=='__main__':main()
