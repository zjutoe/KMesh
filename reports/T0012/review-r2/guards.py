"""Reuse isolated R1 checks, adding two behavioral counterexamples to R2."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t0012_r1_guards',ROOT/'reports/T0012/review-r1/guards.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
original_variants=previous.variants

def variants(source):
    cases=original_variants(source)
    cases['rebuild_exception_with_context']=cases['rebuild_exception'].replace(
        'raise type(exc)(str(exc)) from None','raise type(exc)(str(exc))')
    cases['lazy_dependency_import']=previous.replace_once(source,
        '    if not verify_proof(clauses, query, proof, max_steps=max_steps):',
        '    import kmesh.logic.dependency\n    if not verify_proof(clauses, query, proof, max_steps=max_steps):')
    return cases

previous.variants=variants
if __name__=='__main__':
    previous.main()
