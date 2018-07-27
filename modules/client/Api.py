from default_imports import *

import json
import requests
import time

from modules.game.Game import GameBSONHandler
from modules.game.AnalysedGame import AnalysedGameBSONHandler, AnalysedGame
from modules.client.Env import Env
from modules.client.Job import Job

from requests.models import Response 

from pprint import pprint

class Api(NamedTuple('Api', [
        ('env', Env)
    ])):
    def requestJob(self) -> Opt[Dict]:
        for i in range(5):
            try:
                result = requests.get(f'{self.env.url}/api/request_job', json={'auth': self.env.auth})
                return Job.fromJson(result.json())
            except (json.decoder.JSONDecodeError, requests.ConnectionError, requests.exceptions.SSLError):
                logging.warning("Error in request job. Trying again in 10 sec")
                time.sleep(10)
        return None

    def completeJob(self, job: Job, analysedGames: List[AnalysedGame]) -> Opt[Response]:
        payload = {
            'auth': self.env.auth,
            'job': job.toJson(),
            'analysedGames': [AnalysedGameBSONHandler.writes(ag) for ag in analysedGames] 
        }
        for i in range(5):
            try:
                result = requests.post(f'{self.env.url}/api/complete_job', json=payload)
                return result
            except (json.decoder.JSONDecodeError, requests.ConnectionError, requests.exceptions.SSLError):
                logging.warning('Error in completing job. Trying again in 10 sec')
                time.sleep(10)
        return None