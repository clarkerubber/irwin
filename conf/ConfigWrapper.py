from default_imports import *

import json

class ConfigWrapper:
    """
    Used for loading and accessing values from a json config file.
    """
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
            head, tail = key.split(' ', 1)
            return self.__getattr__(head)[tail]
        except ValueError:
            return self.__getattr__(key)

    @validated
    def __getattr__(self, key: str):
        """
        allows for accessing like, conf.index.like.this
        """
        r = self.d.get(key)
        if isinstance(r, dict):
            return ConfigWrapper(r)
        return r

    def asdict(self) -> Dict:
        return self.d

    def __repr__(self):
        return "ConfigWrapper({})".format(self.d)