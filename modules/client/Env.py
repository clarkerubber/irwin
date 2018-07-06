from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

class Env:
    @validated
    def __init__(self, config: ConfigWrapper):
        self.config = config