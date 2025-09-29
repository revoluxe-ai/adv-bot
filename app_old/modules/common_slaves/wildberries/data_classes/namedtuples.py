from typing import NamedTuple


class KeywordStatForNeo(NamedTuple):
    vector: list[float]
    text: str


class KeywordPhrase(NamedTuple):
    text: str
    words: list[KeywordStatForNeo]
    word2vec: list[float]

    @property
    def dist_to_word(self):
        count_words = len(self.words)
        if count_words:
            return 1 / count_words
        else:
            return 0
