import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from codinator.files import assert_scope, digest, file_info, snapshot, write_json
from codinator.interactive import Interactive
from codinator.process import run_process
from codinator.sandbox import Sandbox

state = Path('/home/mye/.local/state/codinator/interactive')
task_id = 'T0018-heldout-motifs'
db = sqlite3.connect(f'file:{state}/state.sqlite?mode=ro', uri=True)
db.row_factory = sqlite3.Row
task = dict(db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone())
assert (task['state'], task['phase'], task['round'], task['attempt'], task['pid']) == ('accepted', 'done', 2, 2, None)
manifest = json.loads(task['manifest'])
workspace = Path(manifest['workspace'])
task_dir = state / 'tasks' / task_id
attempt = task_dir / 'attempt-0002'
submitted = json.loads((attempt / 'submission.json').read_text())
assert digest(snapshot(workspace, manifest['excludes'])) == digest(submitted) == task['expected_digest']
assert_scope(json.loads((task_dir / 'intake.json').read_text()), submitted, manifest['allowed_paths'])
checked = json.loads(task['review_resume'])
assert checked == json.loads((attempt / 'check-evidence.json').read_text())
assert checked['passed'] and Interactive._evidence_digest(attempt) == checked['digest']
verdict = json.loads((attempt / 'review-delivery/verdict.json').read_text())
assert verdict == json.loads((attempt / 'outcome.json').read_text())
assert verdict['verdict'] == 'accepted' and verdict['issues'] == []
assert verdict['submission_digest'] == task['expected_digest'] and verdict['task_id'] == task_id
checks = {}
for check in manifest['checks']:
    name = check['name']
    p = attempt / 'checks' / name
    launch = json.loads((p / 'launch.json').read_text())
    assert launch['argv'][launch['argv'].index('--') + 1:] == check['argv']
    assert launch['timeout_seconds'] == check['timeout_seconds']
    result = json.loads((p / 'result.json').read_text())
    assert result['exit_code'] == 0 and result['failure'] is None
    for stream, info in result['streams'].items():
        assert file_info(p / stream) == info
    checks[name] = {'result':result,'pytest_summary':(p / 'stdout.txt').read_text().strip().splitlines()[-1]}
review_result = json.loads((attempt / 'codex/result.json').read_text())
assert review_result['exit_code'] == 0 and review_result['failure'] is None
for stream, info in review_result['streams'].items():
    assert file_info(attempt / 'codex' / stream) == info
events = [json.loads(line) for line in (attempt / 'codex/stdout.txt').read_text().splitlines() if line.strip()]
assert any(e.get('type') == 'turn.completed' for e in events)
assert not any(e.get('type') == 'turn.failed' for e in events)
commands = {e['item']['id']:e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution'}
focused = commands['item_20']
assert focused['exit_code'] == 0 and '39 passed' in focused['aggregated_output']
mutation = commands['item_29']
assert mutation['exit_code'] == 0
mutants = [json.loads(line) for line in mutation['aggregated_output'].splitlines() if line.startswith('{')]
assert len(mutants) == 10 and all(m['exit'] == 1 and any('FAILED tests/' in row for row in m['evidence']) for m in mutants)
out = Path(tempfile.mkdtemp(prefix='kmesh-T0018-closeout-'))
print('evidence:', out, flush=True)
write_json(out / 'before.json', {'digest':task['expected_digest'],'evidence_digest':checked['digest'],'state':'accepted'})
env = os.environ | {'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
env.pop('PYTHONPATH', None)
argv = [str(workspace / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp', '/tmp/kmesh-T0018-main-closeout-focused', 'tests/test_heldout_motifs.py']
run_process(Sandbox().wrap(argv, workspace), cwd=workspace, env=env, out=out/'focused', timeout=180)
assert digest(snapshot(workspace, manifest['excludes'])) == task['expected_digest']
assert Interactive._evidence_digest(attempt) == checked['digest']
assert not list((workspace / 'src/kmesh').rglob('*.pyc'))
result = {
    'task_id':task_id,'state':'accepted','round':2,'attempt':2,'accepted_at_epoch':task['updated'],
    'workspace':str(workspace),'head':submitted['git']['head'],'submission_digest':task['expected_digest'],
    'check_evidence_digest':checked['digest'],'controller_checks':checks,
    'files':{p:submitted['files'][p]['sha256'] for p in manifest['allowed_paths']},
    'published_handoff_sha256':hashlib.sha256((task_dir/'handoff.md').read_bytes()).hexdigest(),
    'published_manifest_sha256':hashlib.sha256((task_dir/'manifest.json').read_bytes()).hexdigest(),
    'reviewer_focused':{'event_id':focused['id'],'exit_code':focused['exit_code'],'stdout':focused['aggregated_output']},
    'reviewer_mutants':mutants,'review_result':review_result,
    'closeout_focused':{'result':json.loads((out/'focused/result.json').read_text()),'stdout':(out/'focused/stdout.txt').read_text()},
    'workspace_and_controller_evidence_unchanged':True,'no_bytecode_in_source':True,
    'new_full_rerun':'not_run: verified controller full run and independent focused coverage are sufficient',
    'raw_state':str(task_dir),'closeout_raw':str(out),
}
write_json(out/'summary.json', result)
(out/'verify.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'state':result['state'],'controller_checks':{k:v['pytest_summary'] for k,v in checks.items()},
    'reviewer_mutants_rejected':len(mutants),'closeout_focused':result['closeout_focused']['stdout'].strip(),
    'unchanged':True,'evidence':str(out)},ensure_ascii=False,indent=2),flush=True)
