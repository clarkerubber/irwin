from conf.ConfigWrapper import ConfigWrapper
import enforce

class Env:
    @enforce.runtime_validation
    def __init__(self, settings: ConfigWrapper):
        self.settings = settings

        