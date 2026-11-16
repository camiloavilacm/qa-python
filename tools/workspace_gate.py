"""Combine the local Step 3 gate with the original workspace baseline audit."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];WORKSPACE=ROOT.parent
sys.path.insert(0,str(WORKSPACE/'harness/scripts'))
from common import state,read,audit,write,now
if __name__=='__main__':
    s=state(WORKSPACE);assert s['authorized_step']=='3'
    p=subprocess.run([str(ROOT/'.venv/bin/python'),'harness/scripts/verify_step.py','gate'],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    feature=WORKSPACE/'qa-features'
    assert not subprocess.check_output(['git','-C',str(feature),'status','--porcelain'])
    assert subprocess.check_output(['git','-C',str(feature),'rev-parse','seed-1-approved-v1^{commit}'],text=True).strip()==s['feature_ref']
    result=audit(WORKSPACE,read(WORKSPACE/s['baseline']));assert result['status']=='PASS',json.dumps(result['errors'])
    write(WORKSPACE/'harness/evidence/step3-combined-gate.json',{'step':'3','status':'PASS','time':now(),'feature_ref':s['feature_ref'],'repository_gate':p.stdout,'workspace_scope_audit':result})
    print('PASS: Step 3 local gate, immutable feature and original workspace scope audit')
