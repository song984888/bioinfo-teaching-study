import subprocess
import tempfile
from pathlib import Path
from config import Config


def execute_code(code: str, language: str) -> dict:
    """
    Execute code in a temp file. Returns {stdout, stderr, timeout, returncode}.
    """
    lang_cfg = Config.LANGUAGE_CONFIG.get(language)
    if not lang_cfg:
        return {'stdout': '', 'stderr': f'Unsupported language: {language}', 'timeout': False, 'returncode': 1}

    ext = lang_cfg['ext']
    runner = lang_cfg['runner']

    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        if language in ('java', 'c'):
            # Compile first
            if language == 'java':
                compile_cmd = ['javac', tmp_path]
            else:
                out_path = tmp_path.replace(f'.{ext}', '')
                compile_cmd = ['gcc', tmp_path, '-o', out_path]

            compile_result = subprocess.run(
                compile_cmd, capture_output=True, text=True, timeout=10
            )
            if compile_result.returncode != 0:
                return {'stdout': '', 'stderr': compile_result.stderr, 'timeout': False, 'returncode': compile_result.returncode}

            # Run compiled binary
            if language == 'java':
                run_cmd = ['java', tmp_path.replace('.java', '')]
            else:
                run_cmd = [out_path]
        else:
            run_cmd = [runner, tmp_path]

        result = subprocess.run(
            run_cmd, capture_output=True, text=True, timeout=10
        )
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timeout': False,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'stdout': '', 'stderr': '', 'timeout': True, 'returncode': -1}
    except Exception as e:
        return {'stdout': '', 'stderr': str(e), 'timeout': False, 'returncode': 1}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        # Clean up compiled output
        if language == 'c':
            out_path = tmp_path.replace(f'.{ext}', '')
            Path(out_path).unlink(missing_ok=True)
        if language == 'java':
            class_path = tmp_path.replace('.java', '.class')
            Path(class_path).unlink(missing_ok=True)
