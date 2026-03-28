from django.core.cache import cache


class CacheDependencies:
    def get_from_cache(self, key):
        return cache.get(key)

    def add_to_cache(self, key, value, timeout=600):
        return cache.add(key, value, timeout=timeout)

    def set_from_cache(self, key, value, timeout=60 * 10):
        return cache.set(key, value, timeout=timeout)

    def delete_from_cache(self, key):
        return cache.delete(key)

    def delete_many_from_cache(self, *keys):
        return cache.delete_many(keys)

    def increment(self, key, timeout=60):
        value = cache.get(key)

        if value is None:
            cache.set(key, 1, timeout=timeout)
            return 1

        return cache.incr(key)


cache_deps = CacheDependencies()
