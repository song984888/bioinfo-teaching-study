# Run mode: nohup gunicorn -c gunicorn_conf.py app:app 2>&1 > gunicorn_run.log &

# gunicorn_conf.py
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 4
threads = 8
worker_class = "gthread"

# Timeout
timeout = 600
keepalive = 10

# Logging
accesslog = "./logs/access.log"
errorlog = "./logs/error.log"
loglevel = "info"

# Process naming
proc_name = "flask_app"

# Server mechanics
preload_app = True
max_requests = 1000
max_requests_jitter = 100
