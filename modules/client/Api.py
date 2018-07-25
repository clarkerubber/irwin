from default_imports import *

import json
import requests
import time

from modules.game.Game import GameBSONHandler
from modules.client.Env import Env
from modules.client.Job import Job

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

    def completeJob(self, job: Job) -> Opt[bool]:
        for i in range(4):
            try:
                pass
            except:
                pass