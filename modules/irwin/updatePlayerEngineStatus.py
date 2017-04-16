from modules.irwin.TrainingStats import Sample

def updatePlayerEngineStatus(api, playerAnalysisDB): # For all players in DB, organise them into engine or legit
  for playerAnalysis in playerAnalysisDB.allUnsorted(): # Get all players who have engine = None
    try:
      playerData = api.getPlayerData(playerAnalysis.id)
      engine = isEngine(playerData)
      if engine:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(True))
        playerAnalysisDB.write(playerAnalysis)
      elif engine == False:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(False))
        playerAnalysisDB.write(playerAnalysis)
    except IndexError:
      pass
    except KeyError:
      pass

def isEngine(playerData):
  processed = next((x for x in playerData['history'] if x['type'] == 'report' and x['data']['reason'] == 'cheat'), {}).get('data', {}).get('processedBy', None) is not None
  if playerData['assessment']['user']['engine']:
    return True
  elif processed:
    return False
  return None