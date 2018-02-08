import requests
import logging
import time
import json
from collections import namedtuple

class Api(namedtuple('Api', ['url', 'token'])):
    def postReport(self, report):
        success = False
        attempts = 0
        while not success and attempts < 5:
            attempts += 1
            try:
                response = requests.post(self.url + 'irwin/report?api_key=' + self.token, json=report)
                if response.status_code == 200:
                    success = True
                else:
                    logging.warning(str(response.status_code) + ': Failed to post player report')
                    logging.warning(json.dumps(report))
                    if response.status_code == 413:
                        return
                    logging.debug('Trying again in 60 sec')
                    time.sleep(60)
            except requests.ConnectionError:
                logging.warning("CONNECTION ERROR: Failed to post report.")
                logging.debug("Trying again in 30 sec")
                time.sleep(30)
            except requests.exceptions.SSLError:
                logging.warning("SSL ERROR: Failed to post report.")
                logging.debug("Trying again in 30 sec")
                time.sleep(30)
            except ValueError:
                logging.warning("VALUE ERROR: Failed to post report.")
                logging.debug("Trying again in 30 sec")
                time.sleep(30)

    def getPlayerData(self, userId):
        success = False
        attempts = 0
        output = None
        while not success and attempts < 5:
            attempts += 1
            try:
                response = requests.get(self.url+'irwin/'+userId+'/assessment?api_key='+self.token)
                try:
                    output = json.loads(response.text.decode('utf-8'))
                except json.decoder.JSONDecodeError:
                    logging.warning('Error: JSONDecodeError in getPlayerData for user: ' + str(userId))
                    return None
                success = True
            except requests.ConnectionError:
                logging.warning('CONNECTION ERROR: Failed to pull assessment data')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
            except requests.exceptions.SSLError:
                logging.warning('SSL ERROR: Failed to pull assessment data')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
        return output

    def getNextPlayerId(self):
        success = False
        attempts = 0
        output = None
        while not success and attempts < 5:
            attempts += 1
            try:
                response = requests.get(self.url+'irwin/request?api_key='+self.token)
                if response.status_code == 200:
                    output = response.text
                    success = True
                else:
                    logging.warning(str(response.status_code) + ': Failed get to new player name')
                    logging.debug('Trying again in 60 sec')
                    time.sleep(60)
            except requests.ConnectionError:
                logging.warning('CONNECTION ERROR: Failed to get new player name')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
            except requests.exceptions.SSLError:
                logging.warning('SSL ERROR: Failed to get new player name')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
        return output