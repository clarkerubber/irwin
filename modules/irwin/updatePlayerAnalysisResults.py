def updatePlayerAnalysisResults(api, playerAnalysisDB): # For all players in DB, organise them into engine or legit
  updatedPlayerAnalyses = []
  for playerAnalysis in playerAnalysisDB.unsorted(): # Get all players who have engine = None
    try:
      playerData = api.getPlayerData(playerAnalysis.id)
      processed = next((x for x in playerData['history'] if x['type'] == 'report' and x['data']['reason'] == 'cheat'), {}).get('data', {}).get('processedBy', None) is not None
      if playerData['assessment']['user']['engine']:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(True))
      elif processed:
        updatedPlayerAnalyses.append(playerAnalysis.setEngine(False))
    except IndexError:
      pass
  playerAnalysisDB.lazyWriteMany(updatedPlayerAnalyses)