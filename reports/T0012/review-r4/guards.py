"""R4 review: keep existing controls; check constant case independently."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t0012_r3_guards',ROOT/'reports/T0012/review-r3-codex/guards.py')
r3=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r3)
prior_variants=r3.r2.previous.variants

def variants(source):
    cases=prior_variants(source)
    changed=source.replace('return ("c", term)','return ("c", term.lower())')
    changed=changed.replace('ground_key = (conclusion.pred, conclusion.args[0], conclusion.args[1])',
        'ground_key = (conclusion.pred, conclusion.args[0].lower(), conclusion.args[1].lower())')
    assert changed!=source
    cases['lowercase_constants_only']=changed
    return cases

r3.r2.previous.variants=variants
if __name__=='__main__':
    r3.r2.previous.main()
