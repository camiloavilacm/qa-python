from pathlib import Path
import json,hashlib,re,datetime as dt
from jsonschema import Draft202012Validator,FormatChecker
from .contracts import load
from .observer import REQUIRED

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def status_priority(statuses):return next(x for x in ('error','failed','not_run','passed') if x in statuses)
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def artifact(directory,name,value,kind):
    data=(json.dumps(value,indent=2)+'\n').encode();path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return {'path':name,'sha256':hashlib.sha256(data).hexdigest(),'kind':kind}
def validate(value,directory):
    Draft202012Validator(load('schemas/results.schema.json'),format_checker=FormatChecker()).validate(value)
    assert value['status']==status_priority([s['status']for s in value['scenarios']])
    assert dt.datetime.fromisoformat(value['started_at'])<=dt.datetime.fromisoformat(value['finished_at'])
    assert {s['id']for s in value['scenarios']}=={'AC-1','AC-2','AC-3'}
    for scenario in value['scenarios']:
        observer=scenario['observer'];events=observer['events']
        if scenario['status']=='passed':
            assert observer['state']=='complete'
            assert REQUIRED[scenario['id']]<={(e['method'],e['path'],e['status'],e['authorization_present'])for e in events}
        if observer['state']=='complete':assert REQUIRED[scenario['id']]<={(e['method'],e['path'],e['status'],e['authorization_present'])for e in events}
        for item in scenario['artifacts']:
            path=(directory/item['path']).resolve()
            assert path.is_relative_to(directory.resolve()) and not path.is_symlink()
            data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256']
            # Artifacts are typed projections, never raw HTTP logs or browser traces.
            content=json.loads(data)
            if item['kind']=='network':assert content==observer
            else:assert set(content)=={'scenario','outcome','checks','identity_id','slot_id','execution_id','runner_revision','sut_revision'}
            assert not re.search(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',data)
    return value
