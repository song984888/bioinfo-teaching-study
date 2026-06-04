import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam-system-secret-key-change-in-production')

    OLLAMA_ENDPOINT = os.environ.get('OLLAMA_ENDPOINT', 'http://localhost:11434/api/generate')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'codellama:7b')
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '120'))

    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'songht')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'songht123')
    DB_NAME = os.environ.get('DB_NAME', 'code_exam')
    DB_CHARSET = 'utf8mb4'
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))

    DB_POOL_CONFIG = {
        'host': DB_HOST,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'database': DB_NAME,
        'charset': DB_CHARSET,
        'pool_name': 'exam_pool',
        'pool_size': DB_POOL_SIZE,
        'pool_reset_session': True
    }

    LANGUAGE_CONFIG = {
        'python': {'ext': 'py', 'runner': 'python3', 'name': 'Python'},
        'java':   {'ext': 'java', 'runner': 'javac', 'name': 'Java'},
        'c':      {'ext': 'c', 'runner': 'gcc', 'name': 'C'},
        'perl':   {'ext': 'pl', 'runner': 'perl', 'name': 'Perl'}
    }
