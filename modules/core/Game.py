from collections import namedtuple

from modules.core.PlayerAssessment import PlayerAssessments
from modules.core.Games import Games

import numpy as np

class Game(namedtuple('Game', ['id', 'pgn', 'emts'])):

  def isEmtOutlier(self, emt):
    abs(emt - self.mean) >= self.outlierCutoff

  def emtsNoOutliers(self):
    return [e for e in self.emts if not self.isEmtOutlier(e)]

  def emtStd(self):
    return np.std(self.emtsNoOutliers())

  def emtMean(self):
    return np.mean(self.emtsNoOutliers())

  def __new__(cls, *args, **kvargs):
    self = super().__new__(cls, *args, **kvargs)
    self.mean = np.mean(self.emts)
    self.outlierCutoff = 0.5 * np.std(self.emts)
    return self


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