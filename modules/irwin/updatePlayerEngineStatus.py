from modules.irwin.TrainingStats import Sample
import requests
import threading
import json

def updatePlayerEngineStatus(api, playerAnalysisDB, updateAll): # For all players in DB, organise them into engine or legit
  allUnsorted = playerAnalysisDB.allUnsorted() if not updateAll else playerAnalysisDB.all()
  playerStatuses = api.getPlayerStatuses([playerAnalysis.id for playerAnalysis in allUnsorted])
  for playerAnalysis in allUnsorted: # Get all players who have engine = None
    try:
      engine = isEngine(playerStatuses[playerAnalysis.id])
      if engine is not None:
        playerAnalysisDB.write(playerAnalysis.setEngine(engine))
    except IndexError:
      pass
    except KeyError:
      pass

def isEngine(status):
  if status['engine'] == False and status['report'] == False:
    return False
  elif status['engine'] == True:
    return True
  return None

class PlayerEngineStatusBus(threading.Thread):
  def __init__(self, playerAnalysisDB, config, learner):
    threading.Thread.__init__(self)
    self.playerAnalysisDB = playerAnalysisDB
    self.token = config['api']['token']
    self.url = config['api']['url']
    self.learner = learner

  def run(self):
    while True and self.learner:
      r = requests.get(self.url + 'irwin/stream?api_key=' + self.token, stream=True)
      for line in r.iter_lines():
        lineDict = json.loads(line.decode("utf-8"))
        playerAnalysis = self.playerAnalysisDB.byId(lineDict['user'])
        if playerAnalysis is not None:
          if lineDict['t'] == 'mark':
            playerAnalysis1 = playerAnalysis.setEngine(lineDict['value'])
            self.playerAnalysisDB.write(playerAnalysis1)
          if lineDict['t'] == 'report' and playerAnalysis.engine == False:
            playerAnalysis1 = playerAnalysis.setEngine(None)
            self.playerAnalysisDB.write(playerAnalysis1)

