from bson.objectid import ObjectId
import collections

PlayerAssessment = collections.namedtuple('PlayerAssessment', ['id', 'gameId', 'userId', 'white', 'assessment', 'date', 'sfAvg', 'sfSd', 'mtAvg', 'mtSd', 'blurs', 'hold', 'flags'])

PlayerFlags = collections.namedtuple('PlayerFlags', ['ser', 'aha', 'hbr', 'mbr', 'cmt', 'nfm', 'sha'])

class PlayerAssessments(collections.namedtuple('PlayerAssessments', ['playerAssessments'])):
  def gameIds(self):
    return list([pa.gameId for pa in self.playerAssessments])

  def hasGameId(self, gameId):
    return (gameId in [pa.gameId for pa in self.playerAssessments])

  def byGameIds(self, gameIds):
    return [p for p in self.playerAssessments if p.gameId in gameIds]

  def byGameId(self, gameId):
    return next((p for p in self.playerAssessments if p.gameId == gameId), None)

  def suspicious(self):
    return [p for p in self.list if p.assessment > 2]

def getKey(json, key):
  return json.get(key, False)

class PlayerAssessmentBSONHandler:
  @staticmethod
  def reads(bson):
    f = bson['flags']
    return PlayerAssessment(
      id = bson['_id'],
      gameId = bson['gameId'],
      userId = bson['userId'],
      white = bson['white'],
      assessment = bson['assessment'],
      date = bson['date'],
      sfAvg = bson['sfAvg'],
      sfSd = bson['sfSd'],
      mtAvg = bson['mtAvg'],
      mtSd = bson['mtSd'],
      blurs = bson['blurs'],
      hold = bson['hold'],
      flags = PlayerFlags(
        ser = getKey(f, 'ser'),
        aha = getKey(f, 'aha'),
        hbr = getKey(f, 'hbr'),
        mbr = getKey(f, 'mbr'),
        cmt = getKey(f, 'cmt'),
        nfm = getKey(f, 'nfm'),
        sha = getKey(f, 'sha')))

  @staticmethod
  def writes(playerAssessment):
    return {
      '_id': playerAssessment.id,
      'gameId': playerAssessment.gameId,
      'userId': playerAssessment.userId,
      'white': playerAssessment.white,
      'assessment': playerAssessment.assessment,
      'date': playerAssessment.date,
      'sfAvg': playerAssessment.sfAvg,
      'sfSd': playerAssessment.sfSd,
      'mtAvg': playerAssessment.mtAvg,
      'mtSd': playerAssessment.mtSd,
      'blurs': playerAssessment.blurs,
      'hold': playerAssessment.hold,
      'flags': playerAssessment.flags._asdict()
    }

class PlayerAssessmentDB:
  def __init__(self, playerAssessmentColl):
    self.playerAssessmentColl = playerAssessmentColl

  def byId(self, _id): # string
    try:
      return PlayerAssessmentBSONHandler.reads(self.playerAssessmentColl.find_one({'_id': _id}))
    except:
      return None

  def byIds(self, ids): # List[String]
    return PlayerAssessments([PlayerAssessmentBSONHandler.reads(pa) for pa in self.playerAssessmentColl.find({'_id': {'$in': list([i for i in ids])}})])

  def byUserId(self, userId):
    return PlayerAssessments([PlayerAssessmentBSONHandler.reads(pa) for pa in self.playerAssessmentColl.find({'userId': userId})])

  def byGameId(self, gameId):
    try:
      return PlayerAssessmentBSONHandler.reads(self.playerAssessmentColl.find_one({'gameId': gameId}))
    except:
      return None

  def byGameIds(self, gameIds):
    return PlayerAssessments(PlayerAssessmentBSONHandler.reads(self.playerAssessmentColl.find({'gameId': {'$in': gameId}})))

  def write(self, playerAssessment):
    self.playerAssessmentColl.update_one({'_id': playerAssessment.id}, {'$set': PlayerAssessmentBSONHandler.writes(playerAssessment)}, upsert=True)

  def writeMany(self, playerAssessments):
    if len(playerAssessments.playerAssessments) > 0:
      self.playerAssessmentColl.insert_many([PlayerAssessmentBSONHandler.writes(pa) for pa in playerAssessments.playerAssessments])

  def lazyWriteMany(self, playerAssessments):
    [self.write(pa) for pa in playerAssessments.playerAssessments]