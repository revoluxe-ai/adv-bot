from typing import NamedTuple, Union


class KeywordStatForNeo(NamedTuple):
    vector: list[float]
    text: str


class KeywordPhrase(NamedTuple):
    text: str
    words: list[KeywordStatForNeo]
    word2vec: list[float]

    @property
    def dist_to_word(self):
        return 1/len(self.words)


