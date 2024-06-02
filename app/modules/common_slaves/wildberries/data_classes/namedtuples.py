from typing import NamedTuple, Union


class KeywordStatForNeo(NamedTuple):
    vector: list[float]
    text: str


class KeywordPhrase(NamedTuple):
    text: str
    ctr: Union[float, None]
    words: list[KeywordStatForNeo]
    target_nmids: list[int]
    word2vec: list[float]

    @property
    def dist_to_word(self):
        return 1/len(self.words)


