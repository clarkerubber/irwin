from collections import namedtuple
import math
import numpy as np

class Blurs(namedtuple('Blurs', ['nb', 'moves'])):
  @staticmethod
  def fromDict(d, l):
    moves = [i == '1' for i in list(d.get('bits', ''))]
    moves += [False] * (l - len(moves))
    return Blurs(
      nb = d.get('nb', 0),
      moves = moves
    )

class Score(namedtuple('Score', ['cp', 'mate'])):
  @staticmethod
  def fromDict(d):
    return Score(d.get('cp', None), d.get('mate', None))

  def toDict(self):
    return {'cp': self.cp} if self.cp is not None else {'mate': self.mate}

  def winningChances(self, white):
    if self.mate is not None:
      base = (1 if self.mate > 0 else 0)
    else:
      base = 1 / (1 + math.exp(-0.004 * self.cp))
    return 100*(base if white else (1-base))

class Game(namedtuple('Game', ['id', 'white', 'black', 'pgn', 'emts', 'whiteBlurs', 'blackBlurs', 'analysis'])):
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
      blackBlurs = Blurs.fromDict(d['blurs']['black'], math.floor(len(pgn)/2)),
      analysis = [Score.fromDict(a) for a in d.get('analysis', []) if a is not None]
    )

  def tensor(self, userId):
    if self.analysis == [] or self.emts is None and (self.white == userId or self.black == userId):
      return None

    white = (self.white == userId)
    blurs = self.whiteBlurs.moves if white else self.blackBlurs.moves

    analysis = self.analysis[1:] if white else self.analysis
    analysis = list(zip(analysis[0::2],analysis[1::2]))

    emts = self.emtsByColour(white)
    avgEmt = np.average(emts)
    tensors = [Game.moveTensor(a, b, e, avgEmt, white) for a, b, e in zip(analysis, blurs, emts)]
    tensors = (max(0, 100-len(tensors)))*[Game.nullTensor()] + tensors
    return tensors[:100]

  def emtsByColour(self, white):
    return self.emts[(0 if white else 1)::2]

  @staticmethod
  def moveTensor(analysis, blur, emt, avgEmt, white):
    return [
      analysis[1].winningChances(white),
      (analysis[0].winningChances(white) - analysis[1].winningChances(white)),
      int(blur),
      emt,
      100*((emt - avgEmt)/(avgEmt + 1e-8)),
    ]

  @staticmethod
  def nullTensor():
    return [0, 0, 0, 0, 0]

  @staticmethod
  def ply(moveNumber, white):
    return (2*(moveNumber-1)) + (0 if white else 1)

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

class ScoreBSONHandler:
  @staticmethod
  def reads(bson):
    return [Score.fromDict(s) for s in bson]

  def writes(scores):
    return [s.toDict() for s in scores]

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
      blackBlurs = BlursBSONHandler.reads(bson['blackBlurs']),
      analysis = ScoreBSONHandler.reads(bson.get('analysis', [])))

  @staticmethod
  def writes(game):
    return {
      '_id': game.id,
      'white': game.white,
      'black': game.black,
      'pgn': game.pgn,
      'emts': game.emts,
      'whiteBlurs': BlursBSONHandler.writes(game.whiteBlurs),
      'blackBlurs': BlursBSONHandler.writes(game.blackBlurs),
      'analysis': ScoreBSONHandler.writes(game.analysis)
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