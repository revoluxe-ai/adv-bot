from cashews import cache



def setup_redis_cache():
    cache.setup("redis://localhost:6379/0")
