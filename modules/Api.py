import requests
import chess
import logging
import time
import json
from modules.bcolors.bcolors import bcolors
from collections import namedtuple

class Api(namedtuple('Api', ['token'])):
  def postReport(self, report):
    logging.warning('Posting report for ' + report['userId'])
    success = False
    attempts = 0
    while not success and attempts < 5:
      attempts += 1
      try:
        response = requests.post('https://en.lichess.org/irwin/report?api_key=' + self.token, json=report)
        if response.status_code == 200:
          success = True
        else:
          logging.warning(str(response.status_code) + ': Failed to post player report')
          logging.warning(json.dumps(report))
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
    logging.debug('Getting player data for '+userId+'...')
    success = False
    while not success:
      try:
        response = requests.get('https://en.lichess.org/irwin/'+userId+'/assessment?api_key='+self.token)
        success = True
      except requests.ConnectionError:
        logging.warning('CONNECTION ERROR: Failed to pull assessment data')
        logging.debug('Trying again in 30 sec')
        time.sleep(30)
      except requests.exceptions.SSLError:
        logging.warning('SSL ERROR: Failed to pull assessment data')
        logging.debug('Trying again in 30 sec')
        time.sleep(30)
    try:
      return json.loads(response.text)
    except ValueError:
      return {}

  def getPlayerId(self):
    logging.debug('Getting new player ID...')
    success = False
    while not success:
      try:
        response = requests.get('https://en.lichess.org/irwin/request?api_key='+self.token)
        if response.status_code == 200:
          success = True
        else:
          logging.warning(str(response.status_code) + ': Failed get to new player name')
          logging.debug('Trying again in 60 sec')
          time.sleep(60)
      except requests.ConnectionError:
        logging.warning('CONNECTION ERROR: Failed to get new player name')
        logging.debug('Trying again in 30 sec')
        failures += 1
        time.sleep(30)
      except requests.exceptions.SSLError:
        logging.warning('SSL ERROR: Failed to get new player name')
        logging.debug('Trying again in 30 sec')
        failures += 1
        time.sleep(30)
    try:
      return response.text
    except ValueError:
      return None

  @staticmethod
  def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

  def getPlayerStatuses(self, userIds):
    idChunks = Api.chunks(userIds, 10)
    logging.debug('Getting player status for ' + str(len(userIds)) + ' players')
    data = {}
    for idChunk in idChunks:
      ids = ','.join(idChunk)
      success = False
      while not success:
        try:
          response = requests.get('https://en.lichess.org/irwin/users-mark-and-current-report?ids=' + ids + '&api_key=' + self.token)
          if response.status_code == 200:
            success = True
          else:
            logging.warning(str(response.status_code) + ': Failed get to player data')
            logging.debug('Trying again in 60 sec')
            time.sleep(60)
        except requests.ConnectionError:
          logging.warning("CONNECTION ERROR: Failed to get player data.")
          logging.debug("Trying again in 30 sec")
          time.sleep(30)
        except requests.exceptions.SSLError:
          logging.warning("SSL ERROR: Failed to get player data.")
          logging.debug("Trying again in 30 sec")
          time.sleep(30)
      try:
        data = {**data, **json.loads(response.text)}
      except ValueError:
        pass
    return data