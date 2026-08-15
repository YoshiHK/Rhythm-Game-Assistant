from pathlib import Path
import yaml

path = Path('tools/RGA Maintenance Executor.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)

steps = data['jobs']['maintenance-execution']['steps']
for step in steps:
    if 'run' in step:
        text = step['run']
        if 'python <<' in text or 'cat >' in text:
            print('--- STEP', step.get('name'))
            for i, line in enumerate(text.splitlines(), 1):
                if 'PY' in line or 'MD' in line or 'JSON' in line:
                    print(i, repr(line))
            print()
