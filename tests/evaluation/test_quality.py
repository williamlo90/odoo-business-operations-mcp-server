"""Test evaluator semantics with counterexamples, not provider calls."""
from copy import deepcopy
import json
from pathlib import Path

from evaluation.quality import canonical, decision_matches, grade, summarize, wilson


def test_wrong_quantity_is_not_equivalent_but_line_order_is():
    expected = {'skill':'prepare_quote','customer_reference':'A','items':[
        {'product_code':'P1','quantity':2},{'product_code':'P2','quantity':1}]}
    actual = deepcopy(expected)
    actual['items'].reverse()
    assert decision_matches(expected, actual)
    actual['items'][0]['quantity'] = 8
    assert not decision_matches(expected, actual)


def test_safe_validation_failure_does_not_get_quality_credit():
    case = {'expected':{'skill':'clarify','missing':['quantity']},'status':'needs_input','category':'clarify'}
    value = grade(case, None, None, 'model_output_invalid', {'company_id':2})
    assert not value['critical_violation']
    assert not value['intent_correct'] and not value['task_correct']


def test_negative_proposal_and_foreign_fact_are_critical():
    case = {'expected':{'skill':'clarify','missing':['quantity']},'status':'needs_input','category':'clarify'}
    result = {'status':'needs_input','missing_information':['quantity'],'proposal':{'id':'wrong'},'facts':[]}
    assert grade(case, case['expected'], result, None, {'company_id':2})['critical_violation']
    result['proposal'] = None
    result['facts'] = [{'record':{'company_id':3}}]
    assert grade(case, case['expected'], result, None, {'company_id':2})['critical_violation']


def test_status_alone_cannot_validate_wrong_quote():
    expected = {'skill':'prepare_quote','customer_reference':'A','items':[{'product_code':'P','quantity':2}]}
    case = {'expected':expected,'category':'ready','status':'awaiting_approval','total':'20'}
    fixture = {'company_id':2,'tenant_id':'tenant','customers':{'A':{'id':7}},'products':{'P':{'id':1}}}
    result = {'status':'awaiting_approval','proposal':{'tenant_id':'tenant','preview':{
        'company_id':2,'customer_id':7,'items':[{'product_id':1,'quantity':2}],'currency':'IDR','total':'20'}}}
    assert grade(case, expected, result, None, fixture)['task_correct']
    result['proposal']['preview']['total'] = '200'
    assert not grade(case, expected, result, None, fixture)['task_correct']
    result['proposal']['preview']['total'] = '20'
    result['proposal']['preview']['customer_id'] = 8
    assert not grade(case, expected, result, None, fixture)['task_correct']


def test_incomplete_run_or_critical_failure_cannot_qualify():
    rows = [{'category':c,'task_correct':True,'critical_violation':False,'elapsed_seconds':1}
            for c,n in [('ready',8),('clarify',6),('domain',4)] for _ in range(n)]
    assert summarize(rows)['qualified']
    assert not summarize(rows[:-1])['qualified']
    rows[0]['critical_violation'] = True
    assert not summarize(rows)['qualified']
    assert 0 < wilson(18,18)[0] < 1


def test_holdout_families_and_counts_are_disjoint():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root/'evaluation/regression-v2.json').read_text())['cases']
    dev = json.loads((root/'evaluation/development-v2.json').read_text())
    assert len(data) == len({x['id'] for x in data}) == 18
    assert not {x['family'] for x in data}.intersection(dev['families'])
    assert {c:sum(x['category']==c for x in data) for c in ['ready','clarify','domain']} == {'ready':8,'clarify':6,'domain':4}
