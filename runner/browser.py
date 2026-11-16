"""Two drivers; only contract label/role/data-testid locators are exposed."""
import json,os,time
from .observer import Observer
from .contracts import load
class Browser:
    def __init__(self,kind,base):
        self.kind=kind;self.base=base.rstrip('/');self.selectors=load('selectors.json')['selectors'];self.runtime=[]
        fault=os.environ.get('QA_OBSERVER_FAULT')
        self.observer=Observer(self.base,available=fault!='unavailable',fault=fault)
        self.pending={};self.network_messages=[]
        if kind=='playwright':
            from playwright.sync_api import sync_playwright
            self.pw=sync_playwright().start()
            try:
                self.engine=self.pw.chromium.launch(headless=True)
                self.context=self.engine.new_context(service_workers='block')
                self.page=self.context.new_page();self.page.set_default_timeout(8000)
                self.page.on('pageerror',lambda _:self.runtime.append('browser-script-error'))
                self.cdp=self.context.new_cdp_session(self.page)
                self.cdp.send('Network.enable',{'maxTotalBufferSize':10000000,'maxResourceBufferSize':1000000,'enableDurableMessages':True})
                for event in ('Network.requestWillBeSent','Network.responseReceived','Network.loadingFinished','Network.loadingFailed'):
                    self.cdp.on(event,lambda params,event=event:self.network_messages.append({'method':event,'params':params}))
            except Exception:
                self.pw.stop();raise
        else:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            options=webdriver.ChromeOptions();options.add_argument('--headless=new');options.add_argument('--window-size=1280,900')
            if os.environ.get('QA_CHROME_BINARY'):options.binary_location=os.environ['QA_CHROME_BINARY']
            options.set_capability('goog:loggingPrefs',{'performance':'ALL'})
            service=Service(executable_path=os.environ.get('QA_CHROMEDRIVER'))
            self.page=webdriver.Chrome(options=options,service=service)
            self.page.set_page_load_timeout(15);self.page.set_script_timeout(10)
            try:
                self.page.execute_cdp_cmd('Network.enable',{'maxTotalBufferSize':10000000,'maxResourceBufferSize':1000000,'enableDurableMessages':True})
                assert 'performance' in self.page.log_types
                self.page.get_log('performance')
            except Exception:self.observer.available=False
    def drain(self):
        if self.kind=='playwright':self.page.wait_for_timeout(25)
        if not self.observer.available:return
        try:
            if self.kind=='playwright':
                messages,self.network_messages=self.network_messages,[]
            else:messages=[json.loads(entry['message'])['message'] for entry in self.page.get_log('performance')]
            for message in messages:
                method=message['method'];p=message['params'];id=p.get('requestId')
                if method=='Network.requestWillBeSent':
                    req=p['request'];self.observer.request(id,req['method'],req['url'],req.get('headers',{}))
                elif method=='Network.responseReceived' and id in self.observer.requests:
                    self.pending[id]=int(p['response']['status'])
                elif method=='Network.loadingFailed' and id in self.observer.requests:self.observer.errors.append('request-failed')
                elif method=='Tracing.bufferUsage' and p.get('percentFull',0)>.9:self.observer.errors.append('capture-buffer-full')
            # Fetch callers may discard an error body without loadingFinished.
            # A successful CDP body read proves the response bytes are available.
            for id,status in list(self.pending.items()):
                try:
                    body=self.cdp.send('Network.getResponseBody',{'requestId':id}) if self.kind=='playwright' else self.page.execute_cdp_cmd('Network.getResponseBody',{'requestId':id})
                except Exception:continue  # retry until the bounded scenario deadline
                try:
                    if body.get('base64Encoded'):
                        import base64
                        body['body']=base64.b64decode(body['body']).decode()
                    self.observer.finish(id,status,json.loads(body['body']))
                    self.pending.pop(id)
                except Exception:self.observer.errors.append('invalid-response-body')
        except Exception:self.observer.errors.append('performance-capture-failed')
    def wait(self,predicate):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            self.drain()
            try:
                if predicate():return
            except AssertionError:pass
            time.sleep(.025)
        raise AssertionError('Browser or API expectation timed out')
    def wait_api(self,method,path,status):
        if not self.observer.available:raise AssertionError('API instrumentation unavailable')
        self.wait(lambda:any((e['method'],e['path'],e['status'])==(method,path,status) for e in self.observer.events))
        return self.observer.body(method,path,status)
    def go(self,path):
        if self.kind=='playwright':self.page.goto(self.base+path)
        else:self.page.get(self.base+path)
        self.drain()
    def _pw_locator(self,key):
        s=self.selectors[key]
        if s['by']=='label':return self.page.get_by_label(s['value'],exact=True)
        if s['by']=='role':return self.page.get_by_role(s['value'],**({'name':s['name'],'exact':True} if 'name'in s else {}))
        if s['by']=='data-testid':return self.page.get_by_test_id(s['value'])
        raise ValueError('Unsupported selector')
    def _se_elements(self,key):
        s=self.selectors[key]
        assert s['by'] in ('label','role','data-testid')
        # Semantic locator translation, not an alternate selector supplied by tests.
        return self.page.execute_script("""
const s=arguments[0], text=e=>(e.getAttribute('aria-label')||e.textContent).trim();
if(s.by==='label')return Array.from(document.querySelectorAll('label')).filter(l=>l.textContent.trim()===s.value).map(l=>l.control).filter(Boolean);
if(s.by==='data-testid')return Array.from(document.querySelectorAll('[data-testid]')).filter(e=>e.getAttribute('data-testid')===s.value);
const role=e=>e.getAttribute('role')||(e.tagName==='BUTTON'?'button':/^H[1-6]$/.test(e.tagName)?'heading':null);
return Array.from(document.querySelectorAll('[role],button,h1,h2,h3,h4,h5,h6')).filter(e=>role(e)===s.value&&(!('name'in s)||text(e)===s.name));
""",s)
    def element(self,key):
        if self.kind=='playwright':return self._pw_locator(key)
        found=self._se_elements(key)
        assert len(found)==1,'Contract selector must match exactly once'
        return found[0]
    def fill(self,key,value):
        if self.kind=='playwright':self.element(key).fill(value)
        else:self.element(key).clear();self.element(key).send_keys(value)
    def click(self,key):self.element(key).click();self.drain()
    def text(self,key):
        if self.kind=='playwright':return self.element(key).inner_text()
        return self.element(key).text
    def count(self,key):return self._pw_locator(key).count() if self.kind=='playwright' else len(self._se_elements(key))
    def visible(self,key):
        return self.element(key).is_visible() if self.kind=='playwright' else self.element(key).is_displayed()
    def evaluate(self,script,*args):
        if self.kind=='playwright':return self.page.evaluate(script,*args)
        return self.page.execute_script('return ('+script+')(...arguments)',*args)
    def storage(self):return self.evaluate('()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage)})')
    def cookies(self):return self.context.cookies() if self.kind=='playwright' else self.page.get_cookies()
    def current_url(self):return self.page.url if self.kind=='playwright' else self.page.current_url
    def authenticated_user(self):
        if self.kind=='playwright':
            return self.page.evaluate("""async()=>{const response=await fetch('/api/user',{headers:{Authorization:'Token '+localStorage.getItem('jwt')}});const body=await response.json();return {status:response.status,email:body.user?.email,username:body.user?.username};}""")
        return self.page.execute_async_script("""const done=arguments[0];fetch('/api/user',{headers:{Authorization:'Token '+localStorage.getItem('jwt')}}).then(async r=>{const b=await r.json();done({status:r.status,email:b.user?.email,username:b.user?.username})}).catch(()=>done({status:0}));""")
    def close(self):
        if self.kind=='playwright':
            try:self.context.close();self.engine.close()
            finally:self.pw.stop()
        else:self.page.quit()
