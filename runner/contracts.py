from pathlib import Path
import json,subprocess,hashlib,configparser
ROOT=Path(__file__).resolve().parents[1]
FEATURES=ROOT/'qa-features'
REF=(ROOT/'feature-ref.txt').read_text().strip()
def load(name):return json.loads((FEATURES/name).read_text())
def verify():
    def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
    assert git('-C',str(FEATURES),'rev-parse','HEAD')==REF, 'Submodule feature_ref moved'
    assert not git('-C',str(FEATURES),'status','--porcelain'), 'Approved submodule is dirty'
    entry=git('ls-files','--stage','qa-features').split()
    assert entry[:2]==['160000',REF], 'Submodule gitlink differs from feature_ref'
    conf=configparser.ConfigParser();conf.read(ROOT/'.gitmodules')
    assert conf['submodule "qa-features"']['url']=='../qa-features.git'
    assert conf['submodule "qa-features"']['path']=='qa-features'
    assert len(conf.sections())==1
    return REF

def source_revision():
    names=['pyproject.toml','requirements.txt','.gitmodules','feature-ref.txt']
    for prefix in ['runner','tests','tools']:
        names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*.py') if '__pycache__' not in p.parts)
    h=hashlib.sha256()
    for name in sorted(names):h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()
