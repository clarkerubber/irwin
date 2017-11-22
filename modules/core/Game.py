from collections import namedtuple
from chess.pgn import read_game
import math

class Blurs(namedtuple('Blurs', ['nb', 'moves'])):
  @staticmethod
  def fromDict(d, l):
    moves = [i == '1' for i in list(d.get('bits', ''))]
    moves += [False] * (l - len(moves))
    return Blurs(
      nb = d.get('nb', 0),
      moves = moves
    )

class Game(namedtuple('Game', ['id', 'white', 'black', 'pgn', 'emts', 'whiteBlurs', 'blackBlurs'])):
  @staticmethod
  def fromDict(gid, userId, d):
    pgn = d['pgn'].split(" ")
    white, black = None, None
    if d['color'] == 'white':
      white = userId
    else:
      black = userId
    return Game(
      id = gid,
      white = white,
      black = black,
      pgn = pgn,
      emts = d.get('emts'),
      whiteBlurs = Blurs.fromDict(d['blurs']['white'], math.ceil(len(pgn)/2)),
      blackBlurs = Blurs.fromDict(d['blurs']['black'], math.floor(len(pgn)/2))
    )

  def getBlur(self, white, moveNumber):
    if white:
      return self.whiteBlurs.moves[moveNumber-1]
    return self.blackBlurs.moves[moveNumber-1]

class BlursBSONHandler:
  @staticmethod
  def reads(bson):
    return Blurs(
      nb = bson['nb'],
      moves = [i == 1 for i in list(bson['bits'])]
      )
  def writes(blurs):
    return {
      'nb': blurs.nb,
      'bits': ''.join(['1' if i else '0' for i in blurs.moves])
    }

class GameBSONHandler:
  @staticmethod
  def reads(bson):
    return Game(
      id = bson['_id'],
      white = bson.get('white'),
      black = bson.get('black'),
      pgn = bson['pgn'],
      emts = bson['emts'],
      whiteBlurs = BlursBSONHandler.reads(bson['whiteBlurs']),
      blackBlurs = BlursBSONHandler.reads(bson['blackBlurs']))

  @staticmethod
  def writes(game):
    return {
      '_id': game.id,
      'white': game.white,
      'black': game.black,
      'pgn': game.pgn,
      'emts': game.emts,
      'whiteBlurs': BlursBSONHandler.writes(game.whiteBlurs),
      'blackBlurs': BlursBSONHandler.writes(game.blackBlurs)
    }

class GameDB(namedtuple('GameDB', ['gameColl'])):
  def byId(self, _id):
    return GameBSONHandler.reads(self.gameColl.find_one({'_id': _id}))

  def byIds(self, ids): # List[Ids]
    return list([GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': [i for i in ids]}})])

  def byUserId(self, uid):
    return list([GameBSONHandler.reads(g) for g in self.gameColl.find({"$or": [{"white": uid}, {"black": uid}]})])

  def write(self, game): # Game
    self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

  def writeGames(self, games): # Games
    if len(games) > 0:
      self.gameColl.insert_many([GameBSONHandler.writes(g) for g in games])

  def lazyWriteGames(self, games):
    [self.write(g) for g in games]