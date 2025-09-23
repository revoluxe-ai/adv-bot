import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class KeywordStatForNeo(NamedTuple):
    vector: list[float]
    text: str


class KeywordPhrase(NamedTuple):
    text: str
    words: list[KeywordStatForNeo]
    word2vec: list[float]

    @property
    def dist_to_word(self) -> float:
        count_words = len(self.words)
        if count_words:
            logger.error("Нет слов в keywordphrase")
            dist = 1 / len(self.words)
            return dist
        else:
            return 0
