from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.EngineTools import EngineTools

class Env:
    def __init__(self, config: ConfigWrapper):
        self.config = config
        self.url = "{}://{}:{}".format(self.config.server.protocol, self.config.server.domain, self.config.server.port)
        self.engineTools = EngineTools.new(self.config)
        self.auth = self.config.auth.asdict()