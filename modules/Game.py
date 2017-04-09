from operator import attrgetter

class Game:
  def __init__(self, user_id, white, _id, jsonin):
    self.id = _id
    self.user_id = user_id
    self.white = white
    self.pgn = jsonin['pgn']
    self.emts = jsonin['emts']

  def json(self):
    return {'_id': self.id,
      'user_id': self.user_id,
      'white': self.white,
      'pgn': self.pgn,
      'emts': self.emts}

  def write(self, gameColl):
    gameColl.insert_one(self.json())

def game_length(pgn):
    return len(pgn.split(' '))

def recent_games(assessments, pgns):
    try:
        assessments = sorted(assessments, key = lambda x: (attrgetter('assessment'), attrgetter('date')), reverse=True)
        return list(Game(a.userId, a.white, a.gameId, pgns[a.gameId]) for a in assessments if 
          pgns[a.gameId].get('variant', False) == False and
          pgns[a.gameId].get('emts', False) != False and
          game_length(pgns[a.gameId].get('pgn', '')) > 50)[:5]
    except ValueError:
        return []
    except IndexError:
        return []