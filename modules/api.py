import requests
import chess
import logging
import time
import json
from modules.bcolors.bcolors import bcolors

def postReport(userId, report, token):
    logging.info(bcolors.OKBLUE + 'Posting report for ' + userId + bcolors.ENDC)
    success = False
    while not success:
        try:
            r = requests.post('https://en.lichess.org/mod/' + userId + '/irwin?api_key=' + token, json={'result': bool(report[0]), 'reason': report[1]})
            success = True
        except requests.ConnectionError:
            logging.warning(bcolors.WARNING + "CONNECTION ERROR: Failed to post puzzle.")
            logging.debug("Trying again in 30 sec" + bcolors.ENDC)
            time.sleep(30)
        except requests.exceptions.SSLError:
            logging.warning(bcolors.WARNING + "SSL ERROR: Failed to post puzzle.")
            logging.debug("Trying again in 30 sec" + bcolors.ENDC)
            time.sleep(30)

def getPlayerData(user_id, token):
    logging.debug(bcolors.WARNING + 'Getting player data for '+user_id+'...' + bcolors.ENDC)
    success = False
    while not success:
        try:
            response = requests.get('https://en.lichess.org/mod/'+user_id+'/assessment?api_key='+token)
            success = True
        except requests.ConnectionError:
            logging.warning(bcolors.WARNING + 'CONNECTION ERROR: Failed to pull assessment data' + bcolors.ENDC)
            logging.debug(bcolors.WARNING + 'Trying again in 30 sec' + bcolors.ENDC)
            time.sleep(30)
        except requests.exceptions.SSLError:
            logging.warning(bcolors.WARNING + 'SSL ERROR: Failed to pull assessment data' + bcolors.ENDC)
            logging.debug(bcolors.WARNING + 'Trying again in 30 sec' + bcolors.ENDC)
            time.sleep(30)
    try:
        return json.loads(response.text)
    except ValueError:
        return {}

def getPlayerId(token):
    logging.debug(bcolors.WARNING + 'Getting new player ID...' + bcolors.ENDC)
    success = False
    while not success:
        try:
            response = requests.get('https://en.lichess.org/report/irwin-bot-next?api_key='+token)
            if response.status_code == 200:
                success = True
            else:
                logging.warning(bcolors.WARNING + '404: Failed get to new player name' + bcolors.ENDC)
                logging.debug(bcolors.WARNING + 'Trying again in 60 sec' + bcolors.ENDC)
                time.sleep(60)
        except requests.ConnectionError:
            logging.warning(bcolors.WARNING + 'CONNECTION ERROR: Failed to get new player name' + bcolors.ENDC)
            logging.debug(bcolors.WARNING + 'Trying again in 30 sec' + bcolors.ENDC)
            time.sleep(30)
        except requests.exceptions.SSLError:
            logging.warning(bcolors.WARNING + 'SSL ERROR: Failed to get new player name' + bcolors.ENDC)
            logging.debug(bcolors.WARNING + 'Trying again in 30 sec' + bcolors.ENDC)
            time.sleep(30)
    try:
        return response.text
    except ValueError:
        return None