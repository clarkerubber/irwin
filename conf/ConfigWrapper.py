from default_imports import *

import logging
import json

class ConfigWrapper:
    @validated
    def __init__(self, d: Dict):
        self.d = d

    @staticmethod
    @validated
    def new(filename: str):
        with open(filename) as confFile:
            return ConfigWrapper(json.load(confFile))

    @validated
    def __getitem__(self, key: str):
        """
        allows for accessing like, conf["index items like this"]
        """
        try:
            parts = key.split(' ')
            head, tail = (parts[0], ' '.join(parts[1:]))
            if tail != '':
                return ConfigWrapper(self.d[head])[tail]
            return self.d[head]
        except KeyError:
            return None

    @validated
    def __getattr__(self, key: str):
        """
        allows for accessing like, conf.index.like.this
        """
        try:
            r = self.d[key]
            if type(r) is dict:
                return ConfigWrapper(r)
            return r
        except KeyError:
            return None

    def asdict(self) -> Dict:
        return self.d

    def __str__(self) -> str:
        return "ConfigWrapper(" + str(self.d) + ")"

    def __repr__(self):
        return str(self)