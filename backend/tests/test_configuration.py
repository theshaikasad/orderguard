"""Exercise the actual application bootstrap without reading a developer's secret."""
import os
from pathlib import Path
import subprocess
import sys


def test_application_loads_backend_env_from_any_working_directory(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    code = '''
import os
from pathlib import Path
from unittest.mock import patch
expected = Path(os.environ['EXPECTED_BACKEND']) / '.env'
def load(path):
    assert path == expected
    os.environ['MODEL_API_KEY'] = 'test-only-sentinel'
with patch('dotenv.load_dotenv', side_effect=load) as loader:
    import app.main
    assert loader.call_count == 1
    assert os.environ['MODEL_API_KEY'] == 'test-only-sentinel'
'''
    env = os.environ.copy()
    env.pop('MODEL_API_KEY', None)
    env.update(PYTHONPATH=str(backend), EXPECTED_BACKEND=str(backend))
    result = subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, 'Application environment bootstrap failed'
