from modules.irwin.TrainingStats import Sample

def updatePlayerEngineStatus(api, playerAnalysisDB): # For all players in DB, organise them into engine or legit
  updatedPlayerAnalyses = []
  for playerAnalysis in playerAnalysisDB.allUnsorted(): # Get all players who have engine = None
    try:
      playerData = api.getPlayerData(playerAnalysis.id)
      processed = next((x for x in playerData['history'] if x['type'] == 'report' and x['data']['reason'] == 'cheat'), {}).get('data', {}).get('processedBy', None) is not None
      if playerData['assessment']['user']['engine']:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(True))
        engines += 1
      elif processed:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(False))
        legits += 1
    except IndexError:
      pass
    except KeyError:
      pass
  playerAnalysisDB.lazyWriteMany(updatedPlayerAnalyses)