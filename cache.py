import time
from config import CACHE_EXPIRY

class SimpleCache:
    def __init__(self, expiry=300):
        self.cache = {}
        self.expiry = expiry

    def get(self, key):
        if key in self.cache:
            if time.time() - self.cache[key]['time'] < self.expiry:
                return self.cache[key]['value']
        return None

    def set(self, key, value):
        self.cache[key] = {'value': value, 'time': time.time()}

price_cache = SimpleCache(CACHE_EXPIRY)