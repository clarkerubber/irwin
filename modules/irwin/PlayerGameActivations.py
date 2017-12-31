from collections import namedtuple

PlayerGameActivations = namedtuple('PlayerGameActivations', ['userId', 'engine', 'generalActivations', 'narrowActivations'])

class PlayerGameActivationsBSONHandler:
  @staticmethod
  def reads(bson):
    return PlayerGameActivations(
      userId = bson['_id'], # userId
      engine = bson['engine'],
      generalActivations = bson['generalActivations'],
      narrowActivations = bson['narrowActivations'])

  @staticmethod
  def writes(PlayerGameActivations):
    return {
      '_id': PlayerGameActivations.userId,
      'engine': PlayerGameActivations.engine,
      'generalActivations': PlayerGameActivations.generalActivations,
      'narrowActivations': PlayerGameActivations.narrowActivations
    }

class PlayerGameActivationsDB(namedtuple('PlayerGameActivationsDB', ['playerGameActivationsColl'])):
  def byEngine(self, engine):
    return [PlayerGameActivationsBSONHandler.reads(bson) for bson in self.playerGameActivationsColl.find({'engine': engine}) if len(bson['generalActivations']) >= 7]

  def write(self, playerGameActivations):
    self.playerGameActivationsColl.update_one({'_id': playerGameActivations.userId}, {'$set': PlayerGameActivationsBSONHandler.writes(playerGameActivations)}, upsert=True)

  def lazyWriteMany(self, playerGameActivations):
    [self.write(playerGameActivation) for playerGameActivation in playerGameActivations]