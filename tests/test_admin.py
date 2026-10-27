"""Run: python -m unittest discover -s tests -v (uses an isolated temporary database)."""
import unittest, tempfile, os, sys, json, io, copy, subprocess
from pathlib import Path
TEMP=tempfile.TemporaryDirectory(prefix='washma-cms-tests-')
os.environ['DATA_DIR']=TEMP.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as site
from PIL import Image
from werkzeug.security import generate_password_hash

class AdminTests(unittest.TestCase):
    def setUp(self):
        with site.db() as conn:
            conn.execute('UPDATE content SET document=?',(json.dumps(site.SEED),))
            conn.execute('DELETE FROM attempts')
            conn.execute('UPDATE users SET username=?,password=?,auth_version=1,must_change=1',('admin',generate_password_hash('Admin@123')))
        self.client=site.app.test_client();self.csrf=None
    def login(self,client=None):
        result=(client or self.client).post('/api/admin/login',json={'username':'admin','password':'Admin@123'})
        self.assertEqual(result.status_code,200);self.csrf=result.json['csrf'];return result
    def content(self):return self.client.get('/api/admin/content').json['content']
    def save(self,content,revision=None):return self.client.put('/api/admin/content',json=content,headers={'X-CSRF-Token':self.csrf,'If-Match':str(content['revision'] if revision is None else revision)})
    def test_anonymous_access_and_private_files(self):
        for path in ['/api/admin/content','/api/admin/backup']:
            self.assertEqual(self.client.get(path).status_code,401)
        for path in ['/seed.json','/app.py','/data/portfolio.sqlite3','/data/.session-secret','/templates/index.html','/tests/test_admin.py']:
            self.assertEqual(self.client.get(path).status_code,404)
        self.assertEqual(self.client.put('/api/admin/content',json={}).status_code,401)
    def test_login_cookie_csrf_and_origin(self):
        result=self.login();cookie=result.headers.get('Set-Cookie','');self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        doc=self.content()
        self.assertEqual(self.client.put('/api/admin/content',json=doc).status_code,403)
        self.assertEqual(self.client.put('/api/admin/content',json=doc,headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.save(doc).status_code,200)
    def test_edit_text_on_all_six_pages_and_escape_html(self):
        self.login();doc=self.content()
        for key,page in doc['pages'].items():
            # Change an actual main-page text field, not just its SEO title.
            field=next(f for f in page['fields'] if f['label'].startswith('Main heading'))
            page['texts'][field['id']]='Updated '+key+' <script>alert(1)</script>'
        self.assertEqual(self.save(doc).status_code,200)
        for key,route in site.PAGES.items():
            html=self.client.get('/'+route).get_data(as_text=True)
            self.assertIn('Updated '+key+' &lt;script&gt;',html)
            self.assertNotIn('<script>alert(1)</script>',html)
    def test_collection_add_remove_prices_and_rendering(self):
        self.login();doc=self.content()
        service=copy.deepcopy(doc['services'][0]);service.update(id='new-service',title='Test custom service',price='Starting at $299 per project');doc['services'].append(service)
        award=copy.deepcopy(doc['awards'][0]);award.update(id='real-award',title='Verified test milestone',year='2026',issuer='Test client',sample=False);doc['awards'].append(award)
        project=copy.deepcopy(doc['projects'][0]);project.update(id='new-project',title='Test public project',category='short');doc['projects'].append(project)
        featured=copy.deepcopy(doc['featured'][0]);featured.update(id='new-featured',title='Test featured image');doc['featured'].append(featured)
        result=self.save(doc);self.assertEqual(result.status_code,200);doc=result.json['content']
        for route,needle in [('services.html','Starting at $299 per project'),('awards.html','Verified test milestone'),('portfolio.html','Test public project'),('index.html','Test featured image')]:self.assertIn(needle,self.client.get('/'+route).get_data(as_text=True))
        for key in ['services','awards','projects','featured']:doc[key]=[]
        self.assertEqual(self.save(doc).status_code,200)
        for route in site.PAGES.values():self.assertEqual(self.client.get('/'+route).status_code,200)
    def test_contact_settings_update_everywhere(self):
        self.login();doc=self.content();doc['settings'].update(email='updated@example.com',whatsapp='+923001234567',instagram='https://www.instagram.com/test',youtube='https://www.youtube.com/@test')
        self.assertEqual(self.save(doc).status_code,200)
        for route in site.PAGES.values():
            html=self.client.get('/'+route).get_data(as_text=True);self.assertIn('mailto:updated@example.com',html);self.assertIn('https://www.instagram.com/test',html)
        self.assertIn('https://wa.me/923001234567',self.client.get('/contact.html').get_data(as_text=True))
    def test_themes_save_and_css_changes(self):
        self.login();revision=self.content()['revision']
        for key,theme in site.THEMES.items():
            result=self.client.put('/api/admin/theme',json={'theme':key},headers={'X-CSRF-Token':self.csrf,'If-Match':str(revision)})
            self.assertEqual(result.status_code,200);revision=result.json['revision']
            css=self.client.get('/styles.css').get_data(as_text=True);self.assertIn('--orange:'+theme['primary'],css)
            self.assertEqual(self.content()['theme'],key)
            self.assertIn('--orange:'+theme['primary'],self.client.get('/admin/admin.css').get_data(as_text=True))
    def test_revision_conflict_does_not_overwrite(self):
        self.login();old=self.content();self.assertEqual(self.save(copy.deepcopy(old)).status_code,200)
        self.assertEqual(self.save(old).status_code,409)
    def test_upload_decode_and_replace_profile(self):
        self.login();image=io.BytesIO();Image.new('RGB',(25,20),'red').save(image,'PNG');image.seek(0)
        result=self.client.post('/api/admin/upload',data={'image':(image,'profile.png')},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(result.status_code,200);url=result.json['url'];self.assertTrue(url.endswith('.webp'))
        response=self.client.get(url);self.assertEqual(response.mimetype,'image/webp');response.close()
        doc=self.content();doc['media']['profile']['url']=url;self.assertEqual(self.save(doc).status_code,200)
        for route in ['index.html','about.html']:self.assertIn(url,self.client.get('/'+route).get_data(as_text=True))
        backup=self.client.get('/api/admin/backup');self.assertEqual(backup.mimetype,'application/zip')
    def test_upload_rejects_executable_svg_and_bad_paths(self):
        self.login();result=self.client.post('/api/admin/upload',data={'image':(io.BytesIO(b'<svg onload="alert(1)"></svg>'),'x.svg')},headers={'X-CSRF-Token':self.csrf});self.assertEqual(result.status_code,400)
        doc=self.content();doc['media']['profile']['url']='../../app.py';self.assertEqual(self.save(doc).status_code,400)
        doc=self.content();doc['settings']['instagram']='javascript:alert(1)';self.assertEqual(self.save(doc).status_code,400)
        self.assertEqual(self.client.get('/uploads/../../app.py').status_code,404)
    def test_password_change_invalidates_other_sessions(self):
        other=site.app.test_client();self.login(other);self.login()
        result=self.client.post('/api/admin/password',json={'username':'owner','currentPassword':'Admin@123','newPassword':'CorrectHorse!2026'},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(result.status_code,200)
        self.assertEqual(other.get('/api/admin/content').status_code,401)
        self.assertEqual(self.client.get('/api/admin/session').json['mustChange'],False)
        fresh=site.app.test_client();self.assertEqual(fresh.post('/api/admin/login',json={'username':'admin','password':'Admin@123'}).status_code,401)
        self.assertEqual(fresh.post('/api/admin/login',json={'username':'owner','password':'CorrectHorse!2026'}).status_code,200)
        with site.db() as conn:self.assertNotIn('CorrectHorse',conn.execute('SELECT password FROM users').fetchone()[0])
    def test_login_rate_limit(self):
        for _ in range(10):self.assertEqual(self.client.post('/api/admin/login',json={'username':'admin','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/admin/login',json={'username':'admin','password':'Admin@123'}).status_code,429)
    def test_all_image_bindings_use_saved_library(self):
        self.login();image=io.BytesIO();Image.new('RGB',(15,15),'blue').save(image,'PNG');image.seek(0)
        result=self.client.post('/api/admin/upload',data={'image':(image,'all-images.png')},headers={'X-CSRF-Token':self.csrf})
        url=result.json['url'];doc=self.content()
        for record in doc['media'].values():record['url']=url
        self.assertEqual(self.save(doc).status_code,200)
        home=self.client.get('/index.html').get_data(as_text=True)
        portfolio=self.client.get('/portfolio.html').get_data(as_text=True)
        self.assertGreaterEqual(home.count('src="'+url+'"'),5)
        self.assertGreaterEqual(portfolio.count('src="'+url+'"'),12)
        self.assertIn('src="'+url+'"',self.client.get('/about.html').get_data(as_text=True))
    def test_event_connections_leave_room_for_normal_requests(self):
        held=[]
        try:
            for _ in range(16):self.assertTrue(site.event_slots.acquire(blocking=False));held.append(True)
            self.assertEqual(self.client.get('/api/events').status_code,503)
            self.assertEqual(self.client.get('/health').status_code,200)
        finally:
            for _ in held:site.event_slots.release()
        response=self.client.get('/api/events',buffered=False)
        self.assertEqual(response.status_code,200);response.close()
        self.assertTrue(site.event_slots.acquire(blocking=False));site.event_slots.release()
    def test_persistence_in_separate_process(self):
        self.login();doc=self.content();doc['settings']['email']='persisted@example.com';self.assertEqual(self.save(doc).status_code,200)
        result=subprocess.run([sys.executable,'-c','import app; print(app.document()["settings"]["email"])'],cwd=site.ROOT,env={**os.environ,'DATA_DIR':str(site.DATA)},capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.strip(),'persisted@example.com')

if __name__=='__main__':unittest.main()
