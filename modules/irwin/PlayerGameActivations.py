from collections import namedtuple

PlayerGameActivations = namedtuple('PlayerGameActivations', ['userId', 'engine', 'activations'])

class PlayerGameActivationsBSONHandler:
  @staticmethod
  def reads(bson):
    return PlayerGameActivations(
      userId = bson['_id'], # userId
      engine = bson['engine'],
      activations = bson['activations'])

  @staticmethod
  def writes(PlayerGameActivations):
    return {
      '_id': PlayerGameActivations.userId,
      'engine': PlayerGameActivations.engine,
      'activations': PlayerGameActivations.activations
    }

class PlayerGameActivationsDB(namedtuple('PlayerGameActivationsDB', ['playerGameActivationsColl'])):
  def byEngine(self, engine):
    return [PlayerGameActivationsBSONHandler.reads(bson) for bson in self.playerGameActivationsColl.find({'engine': engine})]

  def write(self, playerGameActivations):
    self.playerGameActivationsColl.update_one({'_id': playerGameActivations.userId}, {'$set': PlayerGameActivationsBSONHandler.writes(playerGameActivations)}, upsert=True)

  def lazyWriteMany(self, playerGameActivations):
    [self.write(playerGameActivation) for playerGameActivation in playerGameActivations]