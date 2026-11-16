"""Bounded, sanitized API observation. Response bodies stay in memory only."""
from urllib.parse import urlsplit
REQUIRED={
 'AC-1':{('POST','/users',201,False),('GET','/user',200,True)},
 'AC-2':{('POST','/users/login',200,False),('GET','/user',200,True)},
 'AC-3':{('POST','/users/login',422,False)},
}
class Observer:
    def __init__(self,base,available=True,fault=None):
        self.base=base.rstrip('/');self.available=available;self.fault=fault
        self.requests={};self.events=[];self.bodies=[];self.errors=[]
    def path(self,url):
        parsed=urlsplit(url);base=urlsplit(self.base)
        if (parsed.scheme,parsed.netloc)!=(base.scheme,base.netloc):return None
        path=parsed.path.removeprefix('/api')
        return path if parsed.path.startswith('/api/') and path in ('/users','/users/login','/user') else None
    def request(self,id,method,url,headers):
        path=self.path(url)
        if path and method in ('GET','POST') and self.available:
            if len(self.requests)>=100:self.errors.append('capture-limit');return
            self.requests[id]={'method':method,'path':path,'authorization_present':any(k.lower()=='authorization' for k in headers),'done':False}
    def finish(self,id,status,body):
        if id not in self.requests:return
        row=self.requests[id]
        if self.fault=='drop-response':return
        if row['done']:return
        if not isinstance(status,int) or not 100<=status<=599:self.errors.append('invalid-status');return
        row['done']=True
        event={k:row[k] for k in ('method','path','authorization_present')}|{'status':status}
        self.events.append(event);self.bodies.append((event,body))
    def report(self,scenario):
        seen={(e['method'],e['path'],e['status'],e['authorization_present']) for e in self.events}
        if not self.available or self.fault=='unavailable':state,detail='unavailable','Instrumentation unavailable'
        elif self.errors or self.fault=='error':state,detail='error','Instrumentation error'
        elif not REQUIRED[scenario]<=seen or any(not row['done'] for row in self.requests.values()):state,detail='partial','Missing required or unfinished API observation'
        else:state,detail='complete',None
        return {'state':state,'events':list(self.events),'detail':detail}
    def body(self,method,path,status):
        for event,body in reversed(self.bodies):
            if (event['method'],event['path'],event['status'])==(method,path,status):return body
        raise AssertionError('Required API response was not observed')
