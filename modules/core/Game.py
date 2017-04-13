from collections import namedtuple

from modules.core.PlayerAssessment import PlayerAssessments
from modules.core.Games import Games

class Game(namedtuple('Game', ['id', 'pgn', 'emts'])):
  def getEmt(self, ply):
    return self.emts[ply]

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

class GameDB(namedtuple('GameDB', ['gameColl'])):
  def byId(self, _id):
    try:
      return GameBSONHandler.reads(self.gameColl.find_one({'_id': _id}))
    except:
      return None

  def byIds(self, ids): # List[Ids]
    return Games(list([GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': [i for i in ids]}})]))

  def write(self, game): # Game
    self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

  def writeGames(self, games): # Games
    if len(games.games) > 0:
      self.gameColl.insert_many([GameBSONHandler.writes(g) for g in games.games])

  def lazyWriteGames(self, games):
    [self.write(g) for g in games.games]