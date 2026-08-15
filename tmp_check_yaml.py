from pathlib import Path
import sys
try:
    import yaml
except Exception as e:
    print('PY_YAML_IMPORT_ERROR', e)
    sys.exit(2)
path = Path('tools/RGA Maintenance Executor.yml')
with path.open('r', encoding='utf-8') as f:
    try:
        yaml.safe_load(f)
        print('YAML_OK')
    except Exception as e:
        print(type(e).__name__, e)
        import traceback; traceback.print_exc()
