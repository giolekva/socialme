class Cache(object):
    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError


class NoCache(object):
    def get(self, key):
        return None

    def set(self, key, value):
        pass
