from operator import attrgetter
from bson.objectid import ObjectId

class Game:
  def __init__(self, userId, white, _id, jsonin):
    self.id = _id
    self.userId = userId
    self.white = white
    self.pgn = jsonin['pgn']
    self.emts = jsonin['emts']

  def __str__(self):
    return str(self.json())

  def json(self):
    return {'_id': self.id,
      'userId': self.userId,
      'white': self.white,
      'pgn': self.pgn,
      'emts': self.emts}

def gameLength(pgn):
    return len(pgn.split(' '))

def recentGames(assessments, pgns):
    try:
        assessments = sorted(assessments, key = lambda x: (attrgetter('assessment'), attrgetter('date')), reverse=True)
        return Games(list(Game(a.userId, a.white, a.gameId, pgns[a.gameId]) for a in assessments if 
          pgns[a.gameId].get('variant', False) == False and
          pgns[a.gameId].get('emts', False) != False and
          gameLength(pgns[a.gameId].get('pgn', '')) > 50)[:5])
    except ValueError:
        return []
    except IndexError:
        return []

# thin wrapper class for multiple games
class Games:
  def __init__(self, gs):
    self.games = gs # List[Game]

  def __str__(self):
    return str([str(g) for g in self.games])

  def json(self):
    return [g.json() for g in self.games]

  def ids(self):
    return [g.id for g in self.games]

# For everything database related
class GameDB:
  def __init__(self, gameColl):
    self.gameColl = gameColl

  def __JSONToGame(self, jsonin):
    return Game(jsonin['userId'], jsonin['white'], jsonin['_id'], jsonin)

  def byId(self, _id):
    try:
      return Game(self.gameColl.find_one({'_id': ObjectId(_id)}))
    except:
      return None # ugly

  def byIds(self, ids): # List[Ids]
    return Games(list([self.__JSONToGame(g) for g in self.gameColl.find({'_id': {'$in': list([ObjectId(i) for i in ids])}})]))

  def byUserId(self, userId):
    return Games(list([self.__JSONToGame(g) for g in self.gameColl.find({'userId': userId})]))

  def writeGame(self, game): # Game
    self.gameColl.update_one({'_id': game.json()['_id']}, {'$set': game.json()}, upsert=True)

  def writeGames(self, games): # Games
    if len(games.games) > 0:
      self.gameColl.insert_many(games.json())

  def lazyWriteGames(self, games):
    [self.writeGame(g) for g in games.games]