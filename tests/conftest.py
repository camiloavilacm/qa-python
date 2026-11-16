from pathlib import Path
import sys,uuid,time,re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from runner.contracts import ROOT,REF,verify,source_revision
from runner.browser import Browser
from runner.results import now,write,artifact,validate,status_priority

def pytest_addoption(parser):
    for name,options in {
      '--driver':dict(choices=['playwright','selenium'],required=True),
      '--sut':dict(choices=['sut-python','sut-node'],required=True),
      '--base-url':dict(required=True),
      '--sut-revision':dict(required=True),
      '--campaign-id':dict(default='local'),
      '--execution-id':dict(default=None),
      '--result-dir':dict(required=True),
    }.items():parser.addoption(name,**options)

def pytest_configure(config):
    verify()
    for tag in ('SEED-1','AC-1','AC-2','AC-3'):config.addinivalue_line('markers',tag+': approved story/AC tag')
    revision=config.getoption('--sut-revision')
    assert re.fullmatch(r'[a-f0-9]{40}([a-f0-9]{24})?',revision),'Real source/image revision required'
    directory=Path(config.getoption('--result-dir')).resolve()
    assert directory.is_relative_to(ROOT/'reports'),'Results must live under reports/'
    assert not directory.exists(),'Refusing to overwrite an execution'
    directory.mkdir(parents=True)
    execution=config.getoption('--execution-id') or uuid.uuid4().hex
    config.qa_directory=directory
    config.qa_result={'schema_version':'1.0','issue_id':'SEED-1','campaign_id':config.getoption('--campaign-id'),'execution_id':execution,'feature_ref':REF,'tooling_ref':None,'slot_id':config.getoption('--sut')+':'+config.getoption('--driver'),'sut_revision':revision,'runner_revision':source_revision(),'started_at':now(),'finished_at':now(),'status':'not_run','scenarios':[{'id':id,'status':'not_run','duration_ms':0,'observer':{'state':'unavailable','events':[],'detail':'Scenario not executed'},'artifacts':[],'error':'Not executed'}for id in ('AC-1','AC-2','AC-3')]}

def pytest_bdd_apply_tag(tag,function):
    getattr(pytest.mark,tag)(function);return True

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield;report=outcome.get_result();setattr(item,'rep_'+report.when,report)
    id=next((m.name for m in item.iter_markers()if m.name in ('AC-1','AC-2','AC-3')),None)
    if id and report.failed:
        row=next(s for s in item.config.qa_result['scenarios']if s['id']==id)
        if report.when=='setup':row.update(status='error',error='Scenario setup failed')
        elif report.when=='teardown':row.update(status='error',error='Scenario teardown or evidence validation failed')

@pytest.fixture
def scenario_state(request):
    id=next(m.name for m in request.node.iter_markers()if m.name in ('AC-1','AC-2','AC-3'))
    row=next(s for s in request.config.qa_result['scenarios']if s['id']==id)
    row.update(status='error',error='Scenario not finalized')
    started=time.monotonic();browser=None
    state={'id':id,'checks':[],'identity_id':None,'expected':None}
    try:
        browser=Browser(request.config.getoption('--driver'),request.config.getoption('--base-url'))
        state['browser']=browser
        yield state
    finally:
        if browser:
            try:browser.drain();observer=browser.observer.report(id)
            except Exception:observer={'state':'error','events':[],'detail':'Observer finalization failed'}
            passed=getattr(request.node,'rep_call',None)and request.node.rep_call.passed
            status='passed'if passed else 'failed'
            if observer['state']!='complete' or browser.runtime:status='error'
            row.update(status=status,duration_ms=(time.monotonic()-started)*1000,observer=observer,error=None if status=='passed'else 'Browser assertion or observation failed')
            directory=request.config.qa_directory
            row['artifacts']=[artifact(directory,id+'/network.json',observer,'network'),artifact(directory,id+'/checks.json',{'scenario':id,'outcome':status,'checks':state['checks'],'identity_id':state['identity_id'],'slot_id':request.config.qa_result['slot_id'],'execution_id':request.config.qa_result['execution_id'],'runner_revision':request.config.qa_result['runner_revision'],'sut_revision':request.config.qa_result['sut_revision']},'log')]
            browser.close()
            assert observer['state']=='complete','Incomplete observation prevents PASS'
        else:row.update(status='error',duration_ms=(time.monotonic()-started)*1000,error='Browser instrumentation unavailable')

def pytest_sessionfinish(session,exitstatus):
    if not hasattr(session.config,'qa_result'):return
    result=session.config.qa_result;result['finished_at']=now();result['status']=status_priority([s['status']for s in result['scenarios']])
    if exitstatus!=0 and result['status']=='passed':
        result['scenarios'][0].update(status='error',error='Pytest execution failed');result['status']='error'
    write(session.config.qa_directory/'results.json',result)
    try:validate(result,session.config.qa_directory)
    except Exception:session.exitstatus=1;return
    if result['status']!='passed':session.exitstatus=1
