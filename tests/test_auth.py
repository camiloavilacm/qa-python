import re,uuid
from pytest_bdd import scenarios,given,when,then,parsers
from runner.contracts import FEATURES,load
scenarios(str(FEATURES/'features/auth/login.feature'))

def check(state,name):state['checks'].append(name)

def expected(state):
    if state['expected']is None:state['expected']=load('data/baseline.json')['users'][0]
    return state['expected']

def assert_user(body,identity):
    assert set(body)=={'user'}
    u=body['user'];assert set(u)=={'username','email','token','bio','image'}
    assert u['email']==identity['email']and u['username']==identity['username']
    assert u['bio']is None and u['image']is None
    assert isinstance(u['token'],str)and re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',u['token'])

@given('the immutable synthetic baseline user exists')
def baseline(scenario_state):
    # Provisioning is SUT-owned; this runner never writes baseline data.
    expected(scenario_state);check(scenario_state,'baseline-fixture-loaded')

@given('a fresh browser context has no authentication state')
def fresh(scenario_state):
    b=scenario_state['browser'];b.go('/login')
    assert b.storage()=={'local':[],'session':[]}and not b.cookies()
    check(scenario_state,'fresh-cookie-and-storage-context')

@given('a new registration identity unique to this execution and matrix slot')
def unique(scenario_state):
    id=uuid.uuid4().hex;data=load('data/baseline.json')
    scenario_state['expected']={'username':'qa_'+id,'email':'qa.'+id+'@example.test','password':data['registration_identity']['password']}
    scenario_state['identity_id']=id

@when('I open the registration page')
def register_page(scenario_state):scenario_state['browser'].go('/register')
@when('I open the login page')
def login_page(scenario_state):scenario_state['browser'].go('/login')

@when('I fill "register.username", "register.email", and "register.password" with that identity')
def fill_register(scenario_state):
    for key in ('username','email','password'):scenario_state['browser'].fill('register.'+key,expected(scenario_state)[key])
@when('I fill "login.email" and "login.password" with the baseline credentials')
def fill_login(scenario_state):
    for key in ('email','password'):scenario_state['browser'].fill('login.'+key,expected(scenario_state)[key])
@when('I fill "login.email" with the baseline email and "login.password" with an invalid password')
def fill_invalid(scenario_state):
    b=scenario_state['browser'];b.fill('login.email',expected(scenario_state)['email']);b.fill('login.password',load('data/baseline.json')['invalid_login_password'])
@when(parsers.parse('I activate "{key}"'))
def activate(scenario_state,key):
    assert key in ('register.submit','login.submit');scenario_state['browser'].click(key)

@then('registration returns a user and a token')
def registered(scenario_state):
    assert_user(scenario_state['browser'].wait_api('POST','/users',201),expected(scenario_state));check(scenario_state,'registration-response-contract')
@then('login returns the baseline user and a token')
def logged_in(scenario_state):
    assert_user(scenario_state['browser'].wait_api('POST','/users/login',200),expected(scenario_state));check(scenario_state,'baseline-login-response-contract')
@then('the browser has an authenticated session for that identity')
@then('the browser has an authenticated session for the baseline user')
def session(scenario_state):
    b=scenario_state['browser'];b.wait(lambda:b.current_url()==b.base+'/settings')
    assert b.storage()=={'local':['jwt'],'session':[]}and not b.cookies()
    user=b.authenticated_user();assert user=={'status':200,'email':expected(scenario_state)['email'],'username':expected(scenario_state)['username']}
    b.wait_api('GET','/user',200);check(scenario_state,'authenticated-current-user-and-storage')
@then('"account.identity" shows that identity\'s email on the protected settings page')
@then('"account.identity" shows the baseline email on the protected settings page')
def identity(scenario_state):
    b=scenario_state['browser'];b.wait(lambda:b.count('account.identity')==1)
    assert b.text('account.identity')==expected(scenario_state)['email']
    check(scenario_state,'protected-identity')
@then('"login.error" displays "Email or password is invalid."')
def rejected(scenario_state):
    b=scenario_state['browser'];body=b.wait_api('POST','/users/login',422)
    assert body=={'errors':{'email or password':['is invalid']}}
    b.wait(lambda:b.count('login.error')==1)
    assert b.text('login.error')=='Email or password is invalid.';check(scenario_state,'rejected-login-response-and-ui')
@then('the browser still has no authentication state')
def no_session(scenario_state):
    b=scenario_state['browser'];assert b.storage()=={'local':[],'session':[]}and not b.cookies();check(scenario_state,'rejection-no-browser-session')
@when('I navigate directly to the protected settings page')
def protected(scenario_state):scenario_state['browser'].go('/settings')
@then('access is denied and the browser is redirected to the login page')
def denied(scenario_state):
    b=scenario_state['browser'];b.wait(lambda:b.current_url()==b.base+'/login');check(scenario_state,'protected-route-denied')
@then('"login.heading" is visible and "account.identity" is absent')
def no_identity(scenario_state):
    b=scenario_state['browser'];b.wait(lambda:b.count('login.heading')==1 and b.visible('login.heading'))
    assert b.count('account.identity')==0
    assert b.storage()=={'local':[],'session':[]}and not b.cookies();check(scenario_state,'protected-identity-absent-and-storage-empty')
