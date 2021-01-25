import cache

from google.appengine.api import memcache


class Memcache(cache.Cache):
    def get(self, key):
        return memcache.get(key)

    def set(self, key, value):
        memcache.set(key, value)
