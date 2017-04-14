from modules.irwin.TrainingStats import Sample

def updatePlayerAnalysisResults(api, playerAnalysisDB): # For all players in DB, organise them into engine or legit
  updatedPlayerAnalyses = []
  engines = 0
  legits = 0
  for playerAnalysis in playerAnalysisDB.unsorted(): # Get all players who have engine = None
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
  playerAnalysisDB.lazyWriteMany(updatedPlayerAnalyses)
  return Sample(
    engines = engines,
    legits = legits)