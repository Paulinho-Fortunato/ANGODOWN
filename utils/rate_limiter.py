from collections import defaultdict
from time import time
from flask import request, abort
import threading

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key, max_requests=30, window=60):
        now = time()
        with self.lock:
            self.requests[key] = [t for t in self.requests[key] if t > now - window]
            if len(self.requests[key]) >= max_requests:
                return False
            self.requests[key].append(now)
            return True

    def check_rate_limit(self):
        ip = request.remote_addr
        if not self.is_allowed(ip):
            abort(429, description="Muitas requisições. Aguarde um momento.")