from modules.core.Game import Game
from modules.core.Games import Games
from modules.core.PlayerAssessment import PlayerAssessment, PlayerAssessments

def recentGames(playerAssessments, gameJSONs):
  try:
    playerAssessments = PlayerAssessments(sorted(playerAssessments.playerAssessments,
      key = lambda x: (x.assessment, x.date), reverse=True))
    gs1 = []
    gs2 = []
    for playerAssessment in playerAssessments.playerAssessments:
      gameJSON = gameJSONs.get(playerAssessment.gameId, None)
      pgn = gameJSON.get('pgn', '')
      if gameJSON is not None and 'variant' not in gameJSON and 'emts' in gameJSON and gameLength(pgn) > 44:
        gs1.append(Game(playerAssessment.gameId, pgn, gameJSON['emts']))
    games1 = Games(gs1[:5])
    
    for gameId, gameJSON in gameJSONs.items():
      pgn = gameJSON.get('pgn', '')
      if not games1.hasId(gameId) and 'variant' not in gameJSON and 'emts' in gameJSON and gameLength(pgn) > 44:
        gs2.append(Game(gameId, pgn, gameJSON['emts']))
    return Games((gs1 + gs2)[:10])
  except ValueError:
    return Games([])
  except IndexError:
    return Games([])

def gameLength(pgn):
    return len(pgn.split(' '))