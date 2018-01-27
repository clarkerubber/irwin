import requests
from requests.exceptions import ChunkedEncodingError
from requests.exceptions import ConnectionError
from requests.packages.urllib3.exceptions import NewConnectionError, ProtocolError, MaxRetryError
from http.client import IncompleteRead
from socket import gaierror
import threading
import json
from pprint import pprint
from time import sleep

class PlayerEngineStatusBus(threading.Thread):
    def __init__(self, playerDB, config):
        threading.Thread.__init__(self)
        self.playerDB = playerDB
        self.token = config['api']['token']
        self.url = config['api']['url']

    def run(self):
        while True:
            try:
                r = requests.get(self.url + 'irwin/stream?api_key=' + self.token, stream=True)
                for line in r.iter_lines():
                    lineDict = json.loads(line.decode("utf-8"))
                    pprint(lineDict)
                    player = self.playerDB.byId(lineDict['user'])
                    if player is not None:
                        if lineDict['t'] == 'mark':
                            self.playerDB.write(player.setEngine(lineDict['value']))
                        elif lineDict['t'] == 'report' and player.engine == False:
                            self.playerDB.write(player.setEngine(None))
            except ChunkedEncodingError:
                print("WARNING: ChunkedEncodingError")
                sleep(20)
                continue
            except ConnectionError:
                print("WARNING: ConnectionError")
                sleep(20)
                continue
            except NewConnectionError:
                print("WARNING: NewConnectionError")
                sleep(20)
                continue
            except ProtocolError:
                print("WARNING: ProtocolError")
                sleep(20)
                continue
            except MaxRetryError:
                print("WARNING: MaxRetryError")
                sleep(20)
                continue
            except IncompleteRead:
                print("WARNING: IncompleteRead")
                sleep(20)
                continue
            except gaierror:
                print("WARNING: gaierror")
                sleep(20)
                continues