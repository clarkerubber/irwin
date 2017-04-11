from operator import attrgetter
from bson.objectid import ObjectId

class Game:
  def __init__(self, _id, pgn, emts):
    self.id = _id
    self.pgn = pgn
    self.emts = emts

  def getEmt(self, ply):
    return self.emts[ply]

  def __str__(self):
    return str(self.json())

  def json(self):
    return {'_id': self.id,
      'pgn': self.pgn,
      'emts': self.emts}

def gameLength(pgn):
    return len(pgn.split(' '))

def recentGames(playerAssessments, gameJSONs):
  try:
    playerAssessments.playerAssessments = sorted(playerAssessments.playerAssessments, key = lambda x: (attrgetter('assessment'), attrgetter('date')), reverse=True)
    return Games(list(Game(pa.gameId, gameJSONs[pa.gameId]['pgn'], gameJSONs[pa.gameId]['emts']) for pa in playerAssessments.playerAssessments if 
      'variant' not in gameJSONs[pa.gameId] and
      'emts' in gameJSONs[pa.gameId] and
      gameLength(gameJSONs[pa.gameId].get('pgn', '')) > 50)[:5])
  except ValueError:
    return []
  except IndexError:
    return []

# thin wrapper class for multiple games
class Games:
  def __init__(self, games):
    self.games = games # List[Game]

  def __str__(self):
    return str([str(g) for g in self.games])

  def json(self):
    return [g.json() for g in self.games]

  def byId(self, gameId):
    return next(iter([g for g in self.games if g.id == gameId]), None)

  def ids(self):
    return [g.id for g in self.games]

  def hasId(self, gameId):
    return (gameId in self.ids())

# For everything database related
def JSONToGame(json):
  return Game(json['_id'], json['pgn'], json['emts'])

class GameDB:
  def __init__(self, gameColl):
    self.gameColl = gameColl

  def byId(self, _id):
    try:
      return Game(self.gameColl.find_one({'_id': ObjectId(_id)}))
    except:
      return None # ugly

  def byIds(self, ids): # List[Ids]
    return Games(list([JSONToGame(g) for g in self.gameColl.find({'_id': {'$in': list([i for i in ids])}})]))

  def write(self, game): # Game
    self.gameColl.update_one({'_id': game.json()['_id']}, {'$set': game.json()}, upsert=True)

  def writeGames(self, games): # Games
    if len(games.games) > 0:
      self.gameColl.insert_many(games.json())

  def lazyWriteGames(self, games):
    [self.write(g) for g in games.games]