"""
Gunicorn configuration for production deployment
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
# Single worker avoids the split-brain problem where upload and generate
# requests land on different processes that each have their own in-memory
# generation_jobs dict. Flask spawns background threads per generation
# request, so one worker handles concurrency without blocking.
workers = 1
worker_class = "sync"
threads = 4          # thread pool inside the single worker for concurrent requests
worker_connections = 1000
timeout = 300  # Longer timeout for AI model inference
keepalive = 2

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "image-to-3d-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None
