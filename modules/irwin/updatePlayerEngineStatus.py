from modules.irwin.TrainingStats import Sample

def updatePlayerEngineStatus(api, playerAnalysisDB): # For all players in DB, organise them into engine or legit
  playerStatuses = api.getPlayerStatuses([playerAnalysis.id for playerAnalysis in playerAnalysisDB.allUnsorted()])
  for userId, status in playerStatuses.items(): # Get all players who have engine = None
    try:
      engine = isEngine(status)
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
