from aiocache import caches

def set_config():
    caches.set_config({
        'default': {
            'cache': "aiocache.RedisCache",
            "host": "127.0.0.1",
            'port': 6379,
            "socket_connect_timeout": 1,
            'serializer': {
                'class': "aiocache.serializers.PickleSerializer"
            },
            'plugins': [
                {'class': "aiocache.plugins.HitMissRatioPlugin"},
                {'class': "aiocache.plugins.TimingPlugin"}
            ]
        }
    })



