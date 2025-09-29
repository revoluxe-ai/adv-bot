"""
Word2Vec gRPC сервис модуль.
"""

__all__ = ["Word2Vec", "Word2VecClient", "Word2VecServiceImpl"]

from .word2vec import Word2Vec
from .word2vec_client.client import Word2VecClient
from .service_impl import Word2VecServiceImpl
