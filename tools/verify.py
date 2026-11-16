"""Registered Step 3 acceptance checks; real browsers against operator-selected SUTs."""
from pathlib import Path
import argparse,json,os,subprocess,sys,uuid,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runner.contracts import verify,source_revision
from runner.results import validate,write

def execute(sut,driver,directory,fault=None,scenario=None):
    key=sut.upper().replace('-','_')
    revision=os.environ['QA_'+key+'_REVISION']
    base=os.environ.get('QA_'+key+'_URL','http://localhost:'+('8001' if sut=='sut-python' else '8002'))
    cmd=[sys.executable,'-m','pytest','--driver',driver,'--sut',sut,'--base-url',base,'--sut-revision',revision,'--campaign-id','step3-acceptance','--result-dir',str(directory)]
    if scenario:cmd+=['-k',scenario]
    env=dict(os.environ);env.pop('QA_OBSERVER_FAULT',None)
    if fault:env['QA_OBSERVER_FAULT']=fault
    proc=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=150)
    (directory.parent/(directory.name+'.log')).write_text(proc.stdout+'\nSTDERR:\n'+proc.stderr)
    assert (directory/'results.json').is_file(),proc.stdout+proc.stderr
    result=json.loads((directory/'results.json').read_text());validate(result,directory)
    assert result['runner_revision']==source_revision()
    assert result['sut_revision']==revision
    return proc.returncode,result

def matrix():
    verify();batch=ROOT/'reports'/uuid.uuid4().hex;batch.mkdir(parents=True)
    entries=[];hashes={}
    for sut in ('sut-python','sut-node'):
        for driver in ('playwright','selenium'):
            directory=batch/(sut+'-'+driver)
            code,result=execute(sut,driver,directory)
            print(result['slot_id'],result['status'],flush=True)
            relative=str(directory.relative_to(ROOT));entries.append(relative)
            hashes[relative]=hashlib.sha256((directory/'results.json').read_bytes()).hexdigest()
            assert code==0 and result['status']=='passed',str(directory)
            assert len(result['scenarios'])==3 and all(s['status']=='passed' for s in result['scenarios'])
    write(ROOT/'reports/latest.json',{'runner_revision':source_revision(),'directories':entries,'hashes':hashes})
    print('RESULT_RECEIPT_SHA256',hashlib.sha256((ROOT/'reports/latest.json').read_bytes()).hexdigest())
    print('PASS: 12 real browser scenarios across four slots')

def verify_saved():
    receipt=json.loads((ROOT/'reports/latest.json').read_text())
    assert receipt['runner_revision']==source_revision()
    slots=set()
    for relative in receipt['directories']:
        directory=(ROOT/relative).resolve();assert directory.is_relative_to(ROOT/'reports')
        assert hashlib.sha256((directory/'results.json').read_bytes()).hexdigest()==receipt['hashes'][relative]
        result=json.loads((directory/'results.json').read_text());validate(result,directory)
        assert result['status']=='passed';slots.add(result['slot_id'])
        for row in result['scenarios']:assert row['observer']['state']=='complete'
    assert slots=={s+':'+d for s in ('sut-python','sut-node') for d in ('playwright','selenium')}
    print('RESULT_RECEIPT_SHA256',hashlib.sha256((ROOT/'reports/latest.json').read_bytes()).hexdigest())

def observers():
    verify_saved()
    # Exercise each non-complete state through both live instrumentation adapters.
    batch=ROOT/'reports'/('faults-'+uuid.uuid4().hex);batch.mkdir()
    for driver in ('playwright','selenium'):
        for fault,expected in [('unavailable','unavailable'),('drop-response','partial'),('error','error')]:
            code,result=execute('sut-python',driver,batch/(driver+'-'+fault),fault,'invalid')
            rows=[s for s in result['scenarios'] if s['status']!='not_run']
            assert code!=0 and result['status']!='passed' and len(rows)==1
            assert rows[0]['observer']['state']==expected,(fault,rows)
    print('PASS: 12 complete observers; unavailable, partial and error cannot PASS on either driver')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',choices=['12-passes','observer-complete'],required=True)
    args=parser.parse_args()
    try:(matrix if args.check=='12-passes' else observers)()
    except Exception as error:print(type(error).__name__+': '+str(error),file=sys.stderr);sys.exit(1)
