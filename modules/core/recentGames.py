from modules.core.Game import Game
from modules.core.Games import Games
from modules.core.PlayerAssessments import PlayerAssessments

def recentGames(playerAssessments, gameJSONs):
  try:
    playerAssessments = PlayerAssessments(sorted(playerAssessments.playerAssessments,
      key = lambda x: (x.assessment, x.date), reverse=True))
    return Games([Game(pa.gameId, gameJSONs[pa.gameId]['pgn'], gameJSONs[pa.gameId]['emts']) for pa in playerAssessments.playerAssessments if 
      'variant' not in gameJSONs[pa.gameId] and
      'emts' in gameJSONs[pa.gameId] and
      gameLength(gameJSONs[pa.gameId].get('pgn', '')) > 44][:5])
  except ValueError:
    return []
  except IndexError:
    return []

def gameLength(pgn):
    return len(pgn.split(' '))