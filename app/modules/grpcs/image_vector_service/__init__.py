"""
Image Vector gRPC сервис модуль.
"""

__all__ = [
    "VGGVectorizer", "ImageVectorClient", "ImageVectorServiceImpl"]

# from .vgg_vectorizer import VGGVectorizer
from .image_vector_client.client import ImageVectorClient
from .service_impl import ImageVectorServiceImpl
