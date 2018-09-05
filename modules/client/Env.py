from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.EngineTools import EngineTools

class Env:
    def __init__(self, config: ConfigWrapper, token: Opt[str] = None):
        self.config = config
        self.url = "{}://{}".format(self.config.server.protocol, self.config.server.domain)
        self.engineTools = EngineTools.new(self.config)
        if token is None:
            self.auth = self.config.auth.asdict()
        else:
            self.auth = {'token': token}