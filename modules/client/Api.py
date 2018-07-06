from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from modules.game.Game import GameBSONHandler

@validated
class Api(NamedTuple('Api', [
        ('config', ConfigWrapper)
    ])):
    @validated
    def request_job(self) -> Opt[Dict]:
        for i in range(5):
            try:
                result = requests.get(f'{self.config.url}/request_job', json=self.request_job_payload)
                


    @property
    def request_job_payload(self) -> Dict:
        return {
            'auth': {
                'token': self.config.token
            }
        }