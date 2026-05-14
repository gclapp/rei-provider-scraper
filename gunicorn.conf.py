"""Gunicorn configuration for REI Provider Scraper"""

bind = "0.0.0.0:5000"
workers = 2
worker_class = "sync"
worker_connections = 1000
keepalive = 2
errorlog = "-"
accesslog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
