from app.utils import redis_manager


async def set_clusters_like_clusters():
    redis_manager.get_all_clusters()  # type: ignore[attr-defined]
