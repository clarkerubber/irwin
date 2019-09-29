import requests
import logging
import time
import json
from collections import namedtuple

class Api(namedtuple('Api', ['url', 'token'])):
    def postReport(self, report):
        reportDict = report.reportDict()
        logging.debug(f'Sending player report: {reportDict}')
        for _ in range(5):
            try:
                response = requests.post(
                    self.url + 'irwin/report',
                    headers = {
                        'User-Agent': 'Irwin',
                        'Authorization': f'Bearer {self.token}'
                    },
                    json = reportDict
                )
                if response.status_code == 200:
                    logging.debug(f'Lichess responded with: {response.text}')
                    return True
                else:
                    logging.warning(str(response.status_code) + ': Failed to post player report')
                    logging.warning(json.dumps(reportDict))
                    if response.status_code == 413:
                        return False
                    logging.debug('Trying again in 60 sec')
                    time.sleep(60)
            except requests.exceptions.ChunkedEncodingError:
                logging.warning("ChunkedEncodingError: Failed to post report.")
                logging.debug("Not attempting to post again")
                return
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
        for _ in range(5):
            try:
                response = requests.get(
                    self.url+'irwin/'+userId+'/assessment',
                    headers = {
                        'User-Agent': 'Irwin',
                        'Authorization': f'Bearer {self.token}'
                    }
                )
                try:
                    return response.json()
                except json.decoder.JSONDecodeError:
                    logging.warning('Error: JSONDecodeError in getPlayerData for user: ' + str(userId))
                    logging.warning('Status Code ' + str(response.status_code))
                    logging.warning('Text: ' + response.text[:200])
                    return None
            except requests.ConnectionError:
                logging.warning('CONNECTION ERROR: Failed to pull assessment data')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
            except requests.exceptions.SSLError:
                logging.warning('SSL ERROR: Failed to pull assessment data')
                logging.debug('Trying again in 30 sec')
                time.sleep(30)
        return False
