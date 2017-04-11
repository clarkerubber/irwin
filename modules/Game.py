from operator import attrgetter
from bson.objectid import ObjectId
from modules.PlayerAssessment import PlayerAssessments
from collections import namedtuple

class Game(namedtuple('Game', ['id', 'pgn', 'emts'])):
  def getEmt(self, ply):
    return self.emts[ply]

def gameLength(pgn):
    return len(pgn.split(' '))

def recentGames(playerAssessments, gameJSONs):
  try:
    playerAssessments = PlayerAssessments(sorted(playerAssessments.playerAssessments,
      key = lambda x: (attrgetter('assessment'), attrgetter('date')), reverse=True))
    return Games(list(Game(pa.gameId, gameJSONs[pa.gameId]['pgn'], gameJSONs[pa.gameId]['emts']) for pa in playerAssessments.playerAssessments if 
      'variant' not in gameJSONs[pa.gameId] and
      'emts' in gameJSONs[pa.gameId] and
      gameLength(gameJSONs[pa.gameId].get('pgn', '')) > 50)[:5])
  except ValueError:
    return []
  except IndexError:
    return []

# thin wrapper class for multiple games
class Games(namedtuple('Games', ['games'])):
  def byId(self, gameId):
    return next(iter([g for g in self.games if g.id == gameId]), None)

  def ids(self):
    return [g.id for g in self.games]

  def hasId(self, gameId):
    return (gameId in self.ids())

class GameBSONHandler:
  @staticmethod
  def reads(bson):
    return Game(
      id = bson['_id'],
      pgn = bson['pgn'],
      emts = bson['emts'])

  @staticmethod
  def writes(game):
    return {
      '_id': game.id,
      'pgn': game.pgn,
      'emts': game.emts
    }

class GameDB:
  def __init__(self, gameColl):
    self.gameColl = gameColl

  def byId(self, _id):
    try:
      return GameBSONHandler(self.gameColl.find_one({'_id': _id}))
    except:
      return None

  def byIds(self, ids): # List[Ids]
    return Games(list([GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': list([i for i in ids])}})]))

  def write(self, game): # Game
    self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

  def writeGames(self, games): # Games
    if len(games.games) > 0:
      self.gameColl.insert_many(list([GameBSONHandler.writes(g) for g in games.games]))

  def lazyWriteGames(self, games):
    [self.write(g) for g in games.games]