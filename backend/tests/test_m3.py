"""M3: actual PostgreSQL, mocked model outputs explicitly injected."""
import json
from uuid import uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, delete, insert
from app.agent_models import Business, Incoming, Product
from app.configuration import settings, save_draft, publish, onboarding, DraftSave, Publish, SetupMessage, empty_business
from app.database import businesses, configuration_versions, orders
from app.store import Store
from app.bootstrap import seed
from app.engine import process
from app.provider import ModelError
from app.main import app, get_store, get_provider
from app import scenarios
from test_agent import MockProvider, quoted, accepted, turn, DATE


def edit(store, change=None):
    d = settings(store)
    config = Business.model_validate_json(json.dumps(d['config']))
    if change:
        change(config)
    return save_draft(store, DraftSave(revision=d['revision'], config=config, questions=[]))


def activate(store, change=None):
    d = edit(store, change)
    return publish(store, Publish(revision=d['revision'], reviewed=True))


def test_draft_publish_and_immutable_versions(store):
    d = edit(store, lambda c:c.products['chocolate'].sizes.update({'1':1200}))
    assert store.catalogue()['products']['chocolate']['sizes']['1']==900
    assert d['active_version']==1
    with pytest.raises(HTTPException):
        publish(store, Publish(revision=0,reviewed=True))
    p = publish(store, Publish(revision=d['revision'],reviewed=True))
    assert p['active_version']==2
    assert store.catalogue()['products']['chocolate']['sizes']['1']==1200
    assert p['versions'][-1]['config']['products']['chocolate']['sizes']['1']==900


def test_historical_order_and_production_survive_price_and_product_changes(store):
    state=accepted(store)
    state.production_snapshot=state.accepted_commitment.model_copy(deep=True)
    state.status='in_production'
    store.save(state)
    activate(store, lambda c:c.products.pop('chocolate'))
    result=turn(store,3,text='Hello again')
    assert result.accepted_commitment==state.accepted_commitment
    assert result.production_snapshot==state.production_snapshot
    assert result.accepted_commitment.terms.configuration_snapshot['products']['chocolate']['sizes']['1']==900
    with store.engine.connect() as conn:
        row=conn.execute(select(orders).where(orders.c.business_id==store.business_id)).mappings().one()
        assert row['accepted_commitment']['terms']['total']==900


def test_changed_config_invalidates_pending_quote_even_same_price(store):
    quoted(store)
    activate(store, lambda c:setattr(c.policy,'deposit_percent',25))
    s=turn(store,2,MockProvider(intents=['accept']),'I confirm')
    assert not s.accepted_commitment and s.offered_terms.deposit==225
    assert s.offered_terms.configuration_version==2


def test_different_business_prices_and_isolation(store):
    bid='test-'+uuid4().hex
    seed(store.engine,bid)
    other=Store(store.engine.url,bid)
    try:
        activate(other,lambda c:c.products['chocolate'].sizes.update({'1':1700}))
        assert quoted(other).offered_terms.total==1700
        assert quoted(store).offered_terms.total==900
        scenarios.start(other,'D')
        scenarios.reset(store)
        with pytest.raises(HTTPException):
            from app.scenarios import load
            load(store,'unknown')
        assert len(other.all())==1
    finally:
        scenarios.reset(other)
        with store.engine.begin() as conn:
            conn.execute(delete(businesses).where(businesses.c.id==bid))


class SetupProvider:
    source='mock'
    def __init__(self,edits,questions=None):self.edits,self.questions=edits,questions or []
    def _request(self,*args):return json.dumps({'edits':self.edits,'questions':self.questions})


def test_natural_language_proposal_has_exact_evidence_and_stays_draft(store):
    text='My business is Bloom Studio, capacity 5 items daily.'
    p=SetupProvider([{'path':'name','value':'Bloom Studio','quote':'Bloom Studio'},
        {'path':'policy.daily_capacity','value':'5','quote':'5 items daily'}])
    d=onboarding(store,p,SetupMessage(revision=0,text=text))
    assert d['config']['name']=='Bloom Studio' and d['config']['policy']['daily_capacity']==5
    assert not d['config']['commercial_reviewed']
    assert store.catalogue()['name']=='The Little Crumb'
    assert d['history'][-1]['source']=='mock'


def test_ambiguous_extra_is_question_not_active_rule(store):
    p=SetupProvider([],['Is the ₹100 eggless charge per item or per kilogram?'])
    d=onboarding(store,p,SetupMessage(revision=0,text='Eggless costs ₹100 extra.'))
    assert d['questions'] and d['config']['customizations']['eggless']==150
    with pytest.raises(HTTPException):publish(store,Publish(revision=d['revision'],reviewed=True))


@pytest.mark.parametrize('edit',[
 {'path':'policy.daily_capacity','value':'100','quote':'5 items'},
 {'path':'policy.pricing','value':'negotiable','quote':'5 items'},
 {'path':'__class__.run','value':'code','quote':'5 items'},
 {'path':'name','value':'wrong','quote':'not in source'},
])
def test_invalid_or_malicious_setup_does_not_mutate_draft(store,edit):
    with pytest.raises(ModelError):onboarding(store,SetupProvider([edit]),SetupMessage(revision=0,text='5 items'))
    assert settings(store)['revision']==0


def test_setup_model_failure_no_canned_success(store):
    class Fails:
        def _request(self,*args):raise ModelError('Unavailable')
    with pytest.raises(ModelError):onboarding(store,Fails(),SetupMessage(revision=0,text='Hi'))
    assert settings(store)['history']==[]


def test_new_business_manual_setup_and_pause(store):
    bid='test-'+uuid4().hex
    with store.engine.begin() as conn:conn.execute(insert(businesses).values(id=bid,config=empty_business(bid).model_dump(mode='json'),active_version=0,paused=True))
    other=Store(store.engine.url,bid)
    try:
        assert settings(other)['issues']
        with pytest.raises(HTTPException):quoted(other)
        config=Business.model_validate(store.catalogue());config.id=bid
        d=save_draft(other,DraftSave(revision=0,config=config))
        publish(other,Publish(revision=d['revision'],reviewed=True))
        with other.transaction():other._session.execute(businesses.update().where(businesses.c.id==bid).values(paused=False))
        # Known UI conversation IDs must not invent a customer FK for a new business.
        s=turn(other,1,MockProvider({'product':'chocolate','size':'1','quantity':'1','date':DATE,'fulfillment':'pickup'}),cid='sales-m12')
        assert s.offered_terms.total==900
    finally:
        with store.engine.begin() as conn:conn.execute(delete(businesses).where(businesses.c.id==bid))


class ScenarioProvider(MockProvider):
    """Explicit test double, never used by the production API."""
    def interpret(self,context):
        import re
        t=context['new_message']['text']
        patches={};intents=['inquiry']
        if t.startswith('I would like'):
            patches={'product':'chocolate','size':'1','quantity':'1','date':re.search(r'\d{4}-\d{2}-\d{2}',t)[0],'fulfillment':'pickup'}
        elif 'Change the size' in t:patches={'size':'1.5'}
        elif t.startswith('Add eggless'):patches={'customizations':'eggless,floral_decoration'}
        elif t.startswith('Change the product'):
            patches={'date':re.search(r'\d{4}-\d{2}-\d{2}',t)[0]}
            for pid,p in context['business']['products'].items():
                if p['name'] in t:patches['product']=pid
        elif t.startswith('Change the date'):patches={'date':re.search(r'\d{4}-\d{2}-\d{2}',t)[0]}
        elif t.startswith('Remove floral'):patches={'customizations':'eggless'}
        elif t=='I confirm' or "I'll take" in t:intents=['accept']
        elif t.startswith('I paid'):intents=['payment_claim']
        elif 'laser hologram' in t:patches={'customizations':'laser_hologram'}
        self.patches,self.intents=patches,intents
        # New provider per call avoids sharing mutable test data in the race.
        return MockProvider(patches,intents).interpret(context)


@pytest.mark.parametrize('scenario',list('ABCDEF'))
def test_scenario_invariants_actual_database_mocked_model(store,scenario):
    before=accepted(store)
    run=scenarios.start(store,scenario)
    while run['status']=='running':run=scenarios.advance(store,ScenarioProvider(),run['id'])
    assert run['status']=='passed',run
    assert run['mode']=='mock'
    assert all(c['passed'] for c in run['checks'])
    assert store.get('demo')==before
    scenarios.reset(store)
    assert store.get('demo')==before
    with pytest.raises(HTTPException):scenarios.load(store,run['id'])


def test_lab_model_error_persisted_and_not_passed(store):
    class Fails(MockProvider):
        def interpret(self,context):raise ModelError('No model available')
    r=scenarios.start(store,'D')
    r=scenarios.advance(store,Fails(),r['id'])
    assert r['status']=='error' and r['observations'][0]['error']=='No model available'
    assert not r['states']
    scenarios.reset(store)


def test_api_setup_to_agent_and_lab(store):
    app.dependency_overrides[get_store]=lambda:store.reopen()
    app.dependency_overrides[get_provider]=lambda:ScenarioProvider()
    try:
        client=TestClient(app)
        d=client.get('/api/settings').json()
        d['config']['products']['chocolate']['sizes']['1']=1900
        r=client.post('/api/settings/draft',json={'revision':d['revision'],'config':d['config'],'questions':[]})
        assert r.status_code==200
        assert client.post('/api/settings/publish',json={'revision':r.json()['revision'],'reviewed':True}).status_code==200
        s=client.post('/api/conversations/http/messages',json={'message_id':'m1','text':f'I would like 1 Chocolate cake, size 1 kg, on {DATE}, pickup.'})
        assert s.status_code==200 and s.json()['offered_terms']['total']==1900
        assert client.post('/api/settings/pause',json={'paused':True}).status_code==200
        assert client.post('/api/conversations/http/messages',json={'message_id':'m2','text':'I confirm'}).status_code==409
        r=client.post('/api/lab/runs',json={'scenario':'B'}).json()
        for _ in range(3):r=client.post(f'/api/lab/runs/{r["id"]}/step',json={'step':r['step']}).json()
        assert r['status']=='passed'
        assert client.post('/api/lab/reset').status_code==200
    finally:
        app.dependency_overrides.clear()


def test_ambiguous_charge_rejected_even_if_model_proposes_it(store):
    p=SetupProvider([{'path':'customizations.eggless','value':'100','quote':'Eggless costs ₹100 extra'}])
    d=onboarding(store,p,SetupMessage(revision=0,text='Eggless costs ₹100 extra'))
    assert d['config']['customizations']['eggless']==150
    assert any('per item' in q for q in d['questions'])


def test_per_size_charges_and_non_cake_variants(store):
    def change(c):
        c.category='Florist'
        c.products['chocolate'].name='Rose bouquet'
        c.products['chocolate'].unit='stems'
        c.customizations['ribbon']=10
        c.extra_units['ribbon']='per_size'
    activate(store,change)
    s=turn(store,1,MockProvider({'product':'chocolate','size':'1.5','quantity':'1','date':DATE,'fulfillment':'pickup','customizations':'ribbon'}))
    assert s.offered_terms.total==1365 and 'cake' not in s.assistant_reply.lower()
    assert 'stems' in s.assistant_reply


def test_duplicate_lab_step_does_not_advance_again(store):
    r=scenarios.start(store,'D')
    first=scenarios.advance(store,ScenarioProvider(),r['id'],0)
    duplicate=scenarios.advance(store,ScenarioProvider(),r['id'],0)
    assert duplicate==first and duplicate['step']==1
    scenarios.reset(store)


BLOOM_MESSAGE = """Hey! I run Bloom & Co., a small flower shop.
We sell a bouquet of 12 red roses for ₹699 and
a mixed flower bouquet for ₹499.
Gift wrapping with a ribbon costs ₹50 extra.
A handwritten greeting card costs ₹30 extra.
Pickup is free.
Delivery costs ₹80 in our service area.
We require at least 24 hours' notice.
We can fulfill only 2 orders per day.
Our prices are fixed and we don't offer discounts.
Please keep replies friendly and casual."""


def bloom_config(store):
    c=Business.model_validate(store.catalogue())
    c.name='Bloom & Co.';c.category='Florist'
    c.products={'red_roses':Product(name='12 red roses bouquet',unit='roses',sizes={'12':699}),
                'mixed_flowers':Product(name='Mixed flower bouquet',unit='bouquet',sizes={'standard':499})}
    # Validate dictionaries as complete product models after constructing a synthetic manual draft.
    d=c.model_dump(mode='json')
    d.update(customizations={'ribbon':50},addons={'greeting_card':30},fulfillment={'pickup':0,'delivery':80},delivery_zones={'delivery':['Indiranagar']})
    d['policy'].update(lead_hours=24,daily_capacity=2,capacity_unit='orders')
    return Business.model_validate_json(json.dumps(d))


def test_bloom_859_accept_price_change_959_and_address_gate(store):
    config=bloom_config(store)
    d=save_draft(store,DraftSave(revision=0,config=config))
    publish(store,Publish(revision=d['revision'],reviewed=True))
    spec={'product':'red_roses','size':'12','quantity':'1','date':DATE,'fulfillment':'delivery','customizations':'ribbon','addons':'greeting_card'}
    s=turn(store,1,MockProvider(spec),cid='roses')
    assert s.offered_terms is None and s.missing_fields==['delivery_address']
    s=turn(store,2,MockProvider({'delivery_address':'18 Garden Lane, Indiranagar, Bengaluru'}),cid='roses')
    assert s.offered_terms.total==859
    s=turn(store,3,MockProvider(intents=['accept']),"Perfect, let's go ahead!",cid='roses')
    assert s.accepted_commitment.terms.total==859 and s.payment=='unknown' and not s.production_snapshot
    activate(store,lambda c:c.products['red_roses'].sizes.update({'12':799}))
    assert store.get('roses').accepted_commitment.terms.total==859
    spec['delivery_address']='18 Garden Lane, Indiranagar, Bengaluru'
    new=turn(store,1,MockProvider(spec),cid='new-roses')
    assert new.offered_terms.total==959
    assert s.accepted_commitment.terms.configuration_version < new.offered_terms.configuration_version


def test_delivery_outside_explicit_service_area_cannot_quote(store):
    d=save_draft(store,DraftSave(revision=0,config=bloom_config(store)))
    publish(store,Publish(revision=d['revision'],reviewed=True))
    s=turn(store,1,MockProvider({'product':'red_roses','size':'12','quantity':'1','date':DATE,'fulfillment':'delivery','delivery_address':'12 Unknown Road, Mysuru'}))
    assert not s.offered_terms and s.decision=='needs_owner'


def test_interpretation_failure_retry_is_atomic(store):
    class Fails(MockProvider):
        def interpret(self,context):raise ModelError('Unavailable')
    with pytest.raises(ModelError):turn(store,1,Fails())
    assert store.get('demo').events==[]
    s=quoted(store)
    duplicate=quoted(store)
    assert s==duplicate


def test_legacy_m2_history_without_new_optional_fields_remains_appendable(store):
    from app.database import conversations
    state=accepted(store)
    old=state.model_dump(mode='json')
    def legacy(obj):
        if isinstance(obj,dict):
            obj.pop('configuration_version',None);obj.pop('configuration_snapshot',None)
            for value in obj.values():legacy(value)
        elif isinstance(obj,list):
            for value in obj:legacy(value)
    legacy(old)
    old.pop('last_turn_metrics',None)
    with store.engine.begin() as conn:conn.execute(conversations.update().where(conversations.c.business_id==store.business_id).values(state=old))
    activate(store,lambda c:c.products.pop('chocolate'))
    result=turn(store,3,text='Hello again')
    assert result.accepted_commitment.terms.total==900
    assert len(result.events)>len(old['events'])


def test_followup_can_resolve_original_sourced_amount_without_repeating_it(store):
    first=onboarding(store,SetupProvider([],['Is ₹100 per item or per kg?']),SetupMessage(revision=0,text='Eggless is ₹100 extra'))
    result=onboarding(store,SetupProvider([{'path':'customizations.eggless','value':'100','quote':'Eggless is ₹100 extra'}]),SetupMessage(revision=first['revision'],text='It is per item.'))
    assert result['config']['customizations']['eggless']==100


def test_per_size_extra_on_named_variant_escalates_without_server_error(store):
    def change(c):
        c.products['chocolate'].sizes={'classic':900}
        c.customizations['ribbon']=20
        c.extra_units['ribbon']='per_size'
    activate(store,change)
    s=turn(store,1,MockProvider({'product':'chocolate','size':'classic','quantity':'1','date':DATE,'fulfillment':'pickup','customizations':'ribbon'}))
    assert s.decision=='needs_owner' and not s.offered_terms


def test_other_product_per_kg_price_does_not_resolve_ambiguous_extra(store):
    text='Chocolate cake is ₹900/kg and eggless costs ₹100 extra.'
    p=SetupProvider([{'path':'customizations.eggless','value':'100','quote':text}])
    d=onboarding(store,p,SetupMessage(revision=0,text=text))
    assert d['config']['customizations']['eggless']==150
    assert d['questions']


def test_written_capacity_is_explicit_not_missing(store):
    p=SetupProvider([{'path':'policy.daily_capacity','value':'2','quote':'two orders per day'}, {'path':'policy.capacity_unit','value':'orders','quote':'two orders per day'}])
    d=onboarding(store,p,SetupMessage(revision=0,text='We can fulfill only two orders per day.'))
    assert d['config']['policy']['daily_capacity']==2 and d['config']['policy']['capacity_unit']=='orders'


@pytest.mark.parametrize('key',['G','H'])
def test_new_scenarios_database_invariants(store,key):
    r=scenarios.start(store,key)
    try:
        while r['status']=='running':r=scenarios.advance(store,ScenarioProvider(),r['id'])
        assert r['status']=='passed',r
    finally:scenarios.reset(store)
