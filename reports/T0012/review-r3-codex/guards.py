"""R3 review: retain ten existing controls and probe two remaining requirements."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t0012_r2_guards',ROOT/'reports/T0012/review-r2/guards.py')
r2=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r2)
prior_variants=r2.previous.variants

def variants(source):
    cases=prior_variants(source)
    call='    if not verify_proof(clauses, query, proof, max_steps=max_steps):'
    cases['consume_generator_before_verify']=r2.previous.replace_once(source,call,
        '    if hasattr(proof, "__next__"):\n        next(proof, None)\n'+call)
    lower=source.replace('return ("c", term)','return ("c", term.lower())')
    lower=lower.replace('atom.pred,','atom.pred.lower(),').replace('head.pred,','head.pred.lower(),')
    lower=lower.replace('ground_key = (conclusion.pred, conclusion.args[0], conclusion.args[1])',
        'ground_key = (conclusion.pred.lower(), conclusion.args[0].lower(), conclusion.args[1].lower())')
    assert lower!=source
    cases['lowercase_actual_symbols']=lower
    return cases

r2.previous.variants=variants
if __name__=='__main__':
    r2.previous.main()
