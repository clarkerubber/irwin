from modules.core.Game import Game
from modules.core.Games import Games
from modules.core.PlayerAssessments import PlayerAssessments

def recentGames(playerAssessments, gameJSONs):
  try:
    playerAssessments = PlayerAssessments(sorted(playerAssessments.playerAssessments,
      key = lambda x: (x.assessment, x.date), reverse=True))
    return Games([Game(pa.gameId, gameJSONs[pa.gameId]['pgn'], gameJSONs[pa.gameId]['emts']) for pa in playerAssessments.playerAssessments if 
      'variant' not in gameJSONs.get(pa.gameId, {}) and
      'emts' in gameJSONs.get(pa.gameId, {}) and
      gameLength(gameJSONs.get(pa.gameId, {}).get('pgn', '')) > 44][:8])
  except ValueError:
    return Games([])
  except IndexError:
    return Games([])

def gameLength(pgn):
    return len(pgn.split(' '))