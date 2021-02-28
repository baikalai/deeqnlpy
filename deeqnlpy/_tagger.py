# -*- coding: utf-8 -*-
import json
from sys import stdout
from typing import IO, Union

from google.protobuf.json_format import MessageToDict

from deeqnlpy._custom_dict import CustomDict
from deeqnlpy._lang_service_client import DeeqLanguageServiceClient
from baikal.language.language_service_pb2 import AnalyzeSyntaxResponse, Morpheme


class Tagged:
    """
    Tagged result.
    It has various output manipulations.
    """
    phrase: str = None
    r: AnalyzeSyntaxResponse = None

    def __init__(self, phrase: str, res: AnalyzeSyntaxResponse):
        """
        constructor, which is used internally.
        :param phrase: requested sentences.
        :param res:
        """
        super().__init__()
        self.phrase = phrase
        self.r = res

        # 빈 응답이 있는 경우를 대비해서 값이 없지 않도록 처리한다.
        if self.r is None:
            self.r = AnalyzeSyntaxResponse()
            self.phrase = ''

    def msg(self) -> AnalyzeSyntaxResponse:
        """
        Protobuf message object containing all of NLP engine.
        """
        return self.r

    def as_json(self) -> Union[None, str, bool, float]:
        """
        convert the message to a json object.
        :return: Json Obejct
        """
        return MessageToDict(self.r)

    def as_json_str(self) -> str:
        """
        a json string representing analyzed sentences.
        :return: json string
        """
        d = MessageToDict(self.r)
        return json.dumps(d, ensure_ascii=False, indent=2)

    def print_as_json(self, out: IO = stdout):
        """
        print the analysis result
        :param out: File, if nothing provided, sys.stdout is used.
        :return: None
        """
        d = MessageToDict(self.r)
        json.dump(d, out, ensure_ascii=False, indent=2)

    @staticmethod
    def _pos(m: Morpheme, join: bool, full: bool):
        if join:
            if full:
                p = f':{m.probability:5.3f}' if m.probability > 0 else ''
                oov = f'#{Morpheme.OutOfVocab.Name(m.out_of_vocab)}' if m.out_of_vocab != 0 else ''
                return f'{m.text.content}/{Morpheme.Tag.Name(m.tag)}{p}{oov}'
            else:
                return f'{m.text.content}/{Morpheme.Tag.Name(m.tag)}'
        else:
            if full:
                return m.text.content,\
                       Morpheme.Tag.Name(m.tag),\
                       Morpheme.OutOfVocab.Name(m.out_of_vocab),\
                       m.probability
            else:
                return m.text.content, Morpheme.Tag.Name(m.tag)

    def pos(self, flatten: bool = True, join: bool = False, full: bool = False) -> []:
        """
        POS tagger to tuple.
        :param flatten : If False, returns original morphs.
        :param join    : If True, returns joined sets of morph and tag.
        :param full    : if True, returns everything of morph result
        """
        if flatten:
            return [Tagged._pos(m, join, full) for s in self.r.sentences
                    for token in s.tokens
                    for m in token.morphemes]
        else:
            return [[Tagged._pos(m, join, full) for m in token.morphemes]
                    for s in self.r.sentences
                    for token in s.tokens]

    def morphs(self) -> []:
        """Parse phrase to morphemes."""
        return [m.text.content for s in self.r.sentences
                for token in s.tokens
                for m in token.morphemes]

    def nouns(self) -> []:
        """Noun extractor."""
        return [m.text.content for s in self.r.sentences
                for token in s.tokens
                for m in token.morphemes
                if m.tag in {Morpheme.Tag.NNP, Morpheme.Tag.NNG, Morpheme.Tag.NP, Morpheme.Tag.NNB}]

    def verbs(self) -> []:
        """Noun extractor."""
        return [m.text.content for s in self.r.sentences
                for token in s.tokens
                for m in token.morphemes
                if m.tag in {Morpheme.Tag.VV}]


class Tagger:
    """Wrapper for `deeq-nlp v1.4.x <https://github.com/deeq-ai>`_.
    'DeeqNLP' is a morphological analyzer developed by Baikal-ai.

    .. code-block:: python
        :emphasize-lines: 1
        >>> import deeqnlpy as dn
        >>> tagger = dn.Tagger(domain="custom")
        >>> print(tagger.morphs('안녕하세요, 반가워요.'))
        ['안녕', '하', '시', '어요', ',', '반갑', '어요', '.']
        >>> print(tagger.nouns('나비 허리에 새파란 초생달이 시리다.'))
        ['나비', '허리', '초생달']
        >>> print(tagger.pos('햇빛이 선명하게 나뭇잎을 핥고 있었다.'))
        [('햇빛', 'NNG'), ('이', 'JKS'), ('선명', 'NNG'), ('하', 'XSA'), ('게', 'EC'), ('나뭇잎', 'NNG'),
         ('을', 'JKO'), ('핥', 'VV'), ('고', 'EC'), ('있', 'VX'), ('었', 'EP'), ('다', 'EF'), ('.', 'SF')]
    :param host         : str. host name for deeq nlp server
    :param port         : int. port  for deeq nlp server
    :param domain       : custom domain name for nlp request
    """

    domain = None
    host = "nlp.deeq.ai"
    post = 5656

    def __init__(self, host: str = None, port: int = 5656, domain: str = None):

        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
        self.domain = domain

        addr = self.host + ':' + str(self.port)
        self.client = DeeqLanguageServiceClient(addr)

    def set_domain(self, domain: str):
        """
        Set domain of custom dict.
        :param domain: domain name of custom dict
        :return: None
        """
        self.domain = domain

    def custom_dict(self, domain: str) -> CustomDict:
        self.domain = domain
        return CustomDict(domain, self.host, self.port)

    def tag(self, phrase: str, auto_split: bool = False) -> Tagged:
        if len(phrase) is 0:
            print("OOPS, no sentences.")
            return Tagged('', None)
        return Tagged(phrase,
                      self.client.analyze_syntax(phrase, self.domain, auto_split))

    def tags(self, phrase: [str]) -> Tagged:
        """
        tag string array.
        :param phrase: array of string
        :return: Tagged result instance
        """
        if len(phrase) is 0:
            print("OOPS, no sentences.")
            return Tagged('', None)
        p = '\n'.join(phrase)
        return Tagged(p,
                      self.client.analyze_syntax(p, self.domain, auto_split=False))

    def pos(self, phrase: str, flatten: bool = True, join: bool = False, full: bool = False) -> []:
        """
        POS tagger.
        :param phrase  : string to analyse
        :param flatten : If False, returns original morphs.
        :param join    : If True, returns joined sets of morph and tag.
        :param full    : if True, returns every things of morph result
        """
        return self.tag(phrase).pos(flatten, join, full)

    def morphs(self, phrase: str) -> []:
        """Parse phrase to morphemes."""
        return self.tag(phrase).morphs()

    def nouns(self, phrase: str) -> []:
        """Noun extractor."""
        return self.tag(phrase).nouns()

    def verbs(self, phrase: str) -> []:
        """Verbs extractor."""
        return self.tag(phrase).verbs()
