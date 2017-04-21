import requests
import chess
import logging
import time
import json
from modules.bcolors.bcolors import bcolors
from collections import namedtuple

class Api(namedtuple('Api', ['token'])):
  def postReport(self, userId, report):
    logging.info('Posting report for ' + userId)
    success = False
    while not success:
      try:
        r = requests.post('https://en.lichess.org/mod/' + userId + '/irwin?api_key=' + self.token, json=report)
        success = True
      except requests.ConnectionError:
        logging.warning("CONNECTION ERROR: Failed to post puzzle.")
        logging.debug("Trying again in 30 sec")
        time.sleep(30)
      except requests.exceptions.SSLError:
        logging.warning("SSL ERROR: Failed to post puzzle.")
        logging.debug("Trying again in 30 sec")
        time.sleep(30)

  def getPlayerData(self, userId):
    logging.debug('Getting player data for '+userId+'...')
    success = False
    while not success:
      try:
        response = requests.get('https://en.lichess.org/mod/'+userId+'/assessment?api_key='+self.token)
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
    failures = 0
    while not success and failures < 3:
      try:
        response = requests.get('https://en.lichess.org/report/irwin-bot-next?api_key='+self.token)
        if response.status_code == 200:
          success = True
        else:
          logging.warning(str(response.status_code) + ': Failed get to new player name')
          logging.debug('Trying again in 60 sec')
          failures += 1
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