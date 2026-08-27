import json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
from flask import Flask, jsonify, render_template, request, session
from db import get_connection

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('CODESPACES','false').lower()=='true', PERMANENT_SESSION_LIFETIME=timedelta(days=7))
PASS_MARK = 60

def err(msg,status=400): return jsonify({'ok':False,'message':msg}),status

def current_user():
    uid=session.get('user_id'); token=session.get('session_token')
    if not uid or not token: return None
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute("SELECT u.id,u.student_id,u.name,u.email,u.role,u.status FROM users u JOIN login_sessions s ON s.user_id=u.id WHERE u.id=%s AND s.session_token=%s AND s.expires_at>UTC_TIMESTAMP() LIMIT 1",(uid,token))
        u=cur.fetchone(); return u if u and u['status']=='Active' else None
    finally: cur.close(); c.close()

def login_required(fn):
    @wraps(fn)
    def w(*a,**kw):
        u=current_user()
        return fn(u,*a,**kw) if u else err('Please log in to continue.',401)
    return w

def staff_required(fn):
    @wraps(fn)
    def w(*a,**kw):
        u=current_user()
        if not u:return err('Please log in to continue.',401)
        if u['role'] not in ('Teacher','Admin'):return err('Teacher or Admin access required.',403)
        return fn(u,*a,**kw)
    return w

def user_json(u): return {'studentId':u['student_id'],'name':u['name'],'email':u['email'],'role':u['role'],'status':u['status']}

@app.get('/')
def home(): return render_template('index.html')

@app.get('/api/health')
def health():
    try:
        c=get_connection(); cur=c.cursor(); cur.execute('SELECT VERSION()'); version=cur.fetchone()[0]; cur.close(); c.close()
        return jsonify({'ok':True,'app':'EduAnimate','database':'MySQL','mysqlVersion':version})
    except Exception as e:return jsonify({'ok':False,'message':str(e)}),500

def start_session(c,uid):
    token=secrets.token_urlsafe(40); expiry=datetime.now(timezone.utc)+timedelta(days=7); cur=c.cursor(dictionary=True)
    cur.execute('DELETE FROM login_sessions WHERE expires_at<=UTC_TIMESTAMP()')
    cur.execute('INSERT INTO login_sessions(session_token,user_id,expires_at) VALUES(%s,%s,%s)',(token,uid,expiry.replace(tzinfo=None)))
    cur.execute('SELECT id,student_id,name,email,role,status FROM users WHERE id=%s',(uid,)); u=cur.fetchone(); c.commit(); cur.close()
    session.permanent=True; session['user_id']=uid; session['session_token']=token
    return jsonify({'ok':True,'user':user_json(u),'expiresAt':expiry.isoformat()})

@app.post('/api/auth/register')
def register():
    d=request.get_json(silent=True) or {}; name=str(d.get('name','')).strip(); email=str(d.get('email','')).strip().lower(); password=str(d.get('password',''))
    if len(name)<2:return err('Enter your full name.')
    if '@' not in email or '.' not in email:return err('Enter a valid email address.')
    if len(password)<6:return err('Password must contain at least 6 characters.')
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute('SELECT id FROM users WHERE email=%s',(email,))
        if cur.fetchone():return err('An account with this email already exists.',409)
        ph=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(); sid='STU-'+uuid.uuid4().hex[:8].upper()
        cur.execute("INSERT INTO users(student_id,name,email,password_hash,role,status) VALUES(%s,%s,%s,%s,'Student','Active')",(sid,name,email,ph)); c.commit(); uid=cur.lastrowid
        return start_session(c,uid)
    finally: cur.close(); c.close()

@app.post('/api/auth/login')
def login():
    d=request.get_json(silent=True) or {}; email=str(d.get('email','')).strip().lower(); password=str(d.get('password',''))
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute('SELECT * FROM users WHERE email=%s LIMIT 1',(email,)); u=cur.fetchone()
        if not u or not bcrypt.checkpw(password.encode(),u['password_hash'].encode()):return err('Invalid email or password.',401)
        if u['status']!='Active':return err('This account has been disabled.',403)
        return start_session(c,u['id'])
    finally: cur.close(); c.close()

@app.post('/api/auth/logout')
def logout():
    token=session.get('session_token')
    if token:
        c=get_connection(); cur=c.cursor(); cur.execute('DELETE FROM login_sessions WHERE session_token=%s',(token,)); c.commit(); cur.close(); c.close()
    session.clear(); return jsonify({'ok':True})

@app.get('/api/me')
@login_required
def me(u): return jsonify({'ok':True,'user':user_json(u)})

@app.get('/api/bootstrap')
@login_required
def bootstrap(u):
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute('SELECT COUNT(*) total FROM topics WHERE published=1'); total=int(cur.fetchone()['total'])
        cur.execute('SELECT COUNT(*) done,COALESCE(AVG(best_score),0) avg FROM progress WHERE user_id=%s AND completed=1',(u['id'],)); p=cur.fetchone(); done=int(p['done'] or 0)
        cur.execute("SELECT t.topic_code FROM topics t LEFT JOIN progress p ON p.topic_id=t.id AND p.user_id=%s WHERE t.published=1 AND COALESCE(p.completed,0)=0 ORDER BY t.id LIMIT 1",(u['id'],)); row=cur.fetchone()
        return jsonify({'ok':True,'user':user_json(u),'stats':{'completedTopics':done,'totalTopics':total,'averageBestScore':round(float(p['avg'] or 0),1),'completionPercent':round(done/total*100 if total else 0,1)},'continueTopicId':row['topic_code'] if row else None})
    finally:cur.close();c.close()

@app.get('/api/subjects')
@login_required
def subjects(u):
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute("SELECT s.code,s.name,s.description,s.icon,COUNT(t.id) topic_count,SUM(CASE WHEN p.completed=1 THEN 1 ELSE 0 END) completed_count FROM subjects s LEFT JOIN topics t ON t.subject_id=s.id AND t.published=1 LEFT JOIN progress p ON p.topic_id=t.id AND p.user_id=%s WHERE s.published=1 GROUP BY s.id ORDER BY s.id",(u['id'],)); rows=cur.fetchall()
        for r in rows:r['topic_count']=int(r['topic_count'] or 0);r['completed_count']=int(r['completed_count'] or 0)
        return jsonify({'ok':True,'subjects':rows})
    finally:cur.close();c.close()

@app.get('/api/subjects/<code>/topics')
@login_required
def subject_topics(u,code):
    c=get_connection(); cur=c.cursor(dictionary=True); code=code.upper()
    try:
        cur.execute('SELECT code,name,description,icon FROM subjects WHERE code=%s AND published=1',(code,)); s=cur.fetchone()
        if not s:return err('Subject not found.',404)
        cur.execute("SELECT t.topic_code,t.title,t.description,t.animation_key,t.sequence_no,COALESCE(p.completed,0) completed,COALESCE(p.best_score,0) best_score,COALESCE(p.attempts,0) attempts FROM topics t LEFT JOIN progress p ON p.topic_id=t.id AND p.user_id=%s WHERE t.subject_id=(SELECT id FROM subjects WHERE code=%s) AND t.published=1 ORDER BY t.sequence_no,t.id",(u['id'],code)); rows=cur.fetchall()
        for r in rows:r['completed']=bool(r['completed']);r['best_score']=float(r['best_score'] or 0)
        return jsonify({'ok':True,'subject':s,'topics':rows})
    finally:cur.close();c.close()

@app.get('/api/topics/<code>')
@login_required
def topic(u,code):
    c=get_connection(); cur=c.cursor(dictionary=True); code=code.upper()
    try:
        cur.execute("SELECT t.id,t.topic_code,t.title,t.description,t.animation_key,t.sequence_no,s.code subject_code,s.name subject_name,l.overview,l.key_points_json,COALESCE(p.completed,0) completed,COALESCE(p.best_score,0) best_score FROM topics t JOIN subjects s ON s.id=t.subject_id JOIN lessons l ON l.topic_id=t.id LEFT JOIN progress p ON p.topic_id=t.id AND p.user_id=%s WHERE t.topic_code=%s AND t.published=1 LIMIT 1",(u['id'],code)); t=cur.fetchone()
        if not t:return err('Topic not found.',404)
        tid=t['id']; t['completed']=bool(t['completed']); t['best_score']=float(t['best_score'] or 0); t['keyPoints']=json.loads(t.pop('key_points_json')) if isinstance(t['key_points_json'],str) else t.pop('key_points_json')
        cur.execute("INSERT INTO progress(user_id,topic_id,last_viewed_at) VALUES(%s,%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE last_viewed_at=UTC_TIMESTAMP()",(u['id'],tid)); c.commit()
        cur.execute('SELECT question_code,question,option_a,option_b,option_c,option_d,sequence_no FROM quiz_questions WHERE topic_id=%s ORDER BY sequence_no,id',(tid,)); qs=cur.fetchall()
        for q in qs:q['options']={'A':q.pop('option_a'),'B':q.pop('option_b'),'C':q.pop('option_c'),'D':q.pop('option_d')}
        cur.execute('SELECT topic_code,title FROM topics WHERE subject_id=(SELECT subject_id FROM topics WHERE id=%s) AND published=1 AND sequence_no<%s ORDER BY sequence_no DESC LIMIT 1',(tid,t['sequence_no'])); prev=cur.fetchone()
        cur.execute('SELECT topic_code,title FROM topics WHERE subject_id=(SELECT subject_id FROM topics WHERE id=%s) AND published=1 AND sequence_no>%s ORDER BY sequence_no ASC LIMIT 1',(tid,t['sequence_no'])); nxt=cur.fetchone(); t.pop('id',None)
        return jsonify({'ok':True,'topic':t,'questions':qs,'navigation':{'previous':prev,'next':nxt}})
    finally:cur.close();c.close()

@app.post('/api/topics/<code>/complete')
@login_required
def complete(u,code):
    c=get_connection(); cur=c.cursor(dictionary=True); cur.execute('SELECT id FROM topics WHERE topic_code=%s AND published=1',(code.upper(),)); r=cur.fetchone()
    if not r:cur.close();c.close();return err('Topic not found.',404)
    cur.execute("INSERT INTO progress(user_id,topic_id,completed,last_viewed_at,completed_at) VALUES(%s,%s,1,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE completed=1,last_viewed_at=UTC_TIMESTAMP(),completed_at=COALESCE(completed_at,UTC_TIMESTAMP())",(u['id'],r['id'])); c.commit();cur.close();c.close();return jsonify({'ok':True})

@app.post('/api/topics/<code>/quiz')
@login_required
def quiz(u,code):
    answers=(request.get_json(silent=True) or {}).get('answers') or {}; c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute('SELECT id FROM topics WHERE topic_code=%s AND published=1',(code.upper(),)); t=cur.fetchone()
        if not t:return err('Topic not found.',404)
        cur.execute('SELECT question_code,question,correct_option,explanation FROM quiz_questions WHERE topic_id=%s ORDER BY sequence_no,id',(t['id'],)); qs=cur.fetchall()
        if any(q['question_code'] not in answers for q in qs):return err('Please answer every question before submitting.')
        score=0; review=[]
        for q in qs:
            sel=str(answers[q['question_code']]).upper(); good=sel==q['correct_option']; score+=int(good); review.append({'questionCode':q['question_code'],'question':q['question'],'selected':sel,'correctOption':q['correct_option'],'correct':good,'explanation':q['explanation']})
        total=len(qs); per=round(score/total*100,2); aid='ATT-'+uuid.uuid4().hex[:14].upper()
        cur.execute('INSERT INTO quiz_attempts(attempt_code,user_id,topic_id,score,total,percentage) VALUES(%s,%s,%s,%s,%s,%s)',(aid,u['id'],t['id'],score,total,per))
        cur.execute("INSERT INTO progress(user_id,topic_id,completed,best_score,attempts,last_viewed_at,completed_at) VALUES(%s,%s,1,%s,1,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE completed=1,best_score=GREATEST(best_score,VALUES(best_score)),attempts=attempts+1,last_viewed_at=UTC_TIMESTAMP(),completed_at=COALESCE(completed_at,UTC_TIMESTAMP())",(u['id'],t['id'],per)); c.commit()
        return jsonify({'ok':True,'score':score,'total':total,'percentage':per,'passed':per>=PASS_MARK,'passMark':PASS_MARK,'review':review})
    finally:cur.close();c.close()

@app.get('/api/progress')
@login_required
def progress(u):
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute("SELECT s.code subject_code,s.name subject_name,t.topic_code,t.title,COALESCE(p.completed,0) completed,COALESCE(p.best_score,0) best_score,COALESCE(p.attempts,0) attempts FROM topics t JOIN subjects s ON s.id=t.subject_id LEFT JOIN progress p ON p.topic_id=t.id AND p.user_id=%s WHERE t.published=1 ORDER BY s.id,t.sequence_no,t.id",(u['id'],)); rows=cur.fetchall()
        for r in rows:r['completed']=bool(r['completed']);r['best_score']=float(r['best_score'] or 0)
        return jsonify({'ok':True,'progress':rows})
    finally:cur.close();c.close()

@app.get('/api/admin/overview')
@staff_required
def admin(u):
    c=get_connection(); cur=c.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) c FROM users WHERE role='Student'"); students=int(cur.fetchone()['c']); cur.execute('SELECT COUNT(*) c FROM topics WHERE published=1'); topics=int(cur.fetchone()['c']); cur.execute('SELECT COUNT(*) c FROM quiz_attempts'); attempts=int(cur.fetchone()['c']); cur.execute('SELECT COALESCE(AVG(percentage),0) a FROM quiz_attempts'); avg=round(float(cur.fetchone()['a'] or 0),1)
        cur.execute("SELECT u.student_id,u.name,u.email,u.status,COUNT(DISTINCT CASE WHEN p.completed=1 THEN p.topic_id END) completed_topics,COALESCE(ROUND(AVG(NULLIF(p.best_score,0)),1),0) average_best_score FROM users u LEFT JOIN progress p ON p.user_id=u.id WHERE u.role='Student' GROUP BY u.id ORDER BY u.created_at DESC"); users=cur.fetchall()
        for r in users:r['completed_topics']=int(r['completed_topics'] or 0);r['average_best_score']=float(r['average_best_score'] or 0)
        cur.execute("SELECT u.name,t.title,a.score,a.total,a.percentage,a.submitted_at FROM quiz_attempts a JOIN users u ON u.id=a.user_id JOIN topics t ON t.id=a.topic_id ORDER BY a.submitted_at DESC LIMIT 20"); recent=cur.fetchall()
        for r in recent:r['percentage']=float(r['percentage']);r['submitted_at']=r['submitted_at'].isoformat()+'Z'
        return jsonify({'ok':True,'counts':{'students':students,'topics':topics,'quizAttempts':attempts,'averageScore':avg},'students':users,'recentAttempts':recent})
    finally:cur.close();c.close()

@app.cli.command('make-admin')
def make_admin():
    email=input('Email to promote: ').strip().lower(); c=get_connection(); cur=c.cursor(); cur.execute("UPDATE users SET role='Admin' WHERE email=%s",(email,)); c.commit(); print(f'{email} is now Admin. Log out and log in again.' if cur.rowcount else 'No user found with that email.'); cur.close();c.close()

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
