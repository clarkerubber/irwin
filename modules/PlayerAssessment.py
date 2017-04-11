from bson.objectid import ObjectId

class PlayerAssessment:
  def __init__(self, _id, gameId, userId, white, assessment, date, sfAvg, sfSd, mtAvg, mtSd, blurs, hold, flags):
    self.id = _id
    self.gameId = gameId
    self.userId = userId
    self.white = white
    self.assessment = assessment
    self.date = date
    self.sfAvg = sfAvg
    self.sfSd = sfSd
    self.mtAvg = mtAvg
    self.mtSd = mtSd
    self.blurs = blurs # percentage 0-100 blur rate
    self.hold = hold # boolean hold alert
    self.flags = flags

  def __str__(self):
    return str(self.json())

  def json(self):
    return {'_id': self.id,
      'gameId': self.gameId,
      'userId': self.userId,
      'white': self.white,
      'assessment': self.assessment,
      'date': self.date,
      'sfAvg': self.sfAvg,
      'sfSd': self.sfSd,
      'mtAvg': self.mtAvg,
      'mtSd': self.mtSd,
      'blurs': self.blurs,
      'hold': self.hold,
      'flags': self.flags.json()}

class PlayerFlags:
  def __init__(self, ser, aha, hbr, mbr, cmt, nfm, sha):
    self.ser = ser # Suspicious Error Rate
    self.aha = aha # Always Has Advantage
    self.hbr = hbr # High Blur Rate
    self.mbr = mbr # Medium Blur Rate
    self.cmt = cmt # Consistent Move Times
    self.nfm = nfm # No Fast Moves
    self.sha = sha # Suspicious Hold Alert

  def json(self):
    return {'ser': self.ser,
      'aha': self.aha,
      'hbr': self.hbr,
      'mbr': self.mbr,
      'cmt': self.cmt,
      'nfm': self.nfm,
      'sha': self.sha}

class PlayerAssessments:
  def __init__(self, playerAssessments):
    self.playerAssessments = playerAssessments # List[PlayerAssesment]

  def __str__(self):
    return str([str(pa) for pa in self.playerAssessments])

  def gameIds(self):
    return list([pa.gameId for pa in self.playerAssessments])

  def hasGameId(self, gameId):
    return (gameId in list([pa.gameId for pa in self.playerAssessments]))

  def byGameIds(self, gameIds):
    return [p for p in self.playerAssessments if p.gameId in gameIds]

  def byGameId(self, gameId):
    return next(iter([p for p in self.playerAssessments if p.gameId == gameId]), None)

  def suspicious(self):
    return [p for p in self.list if p.assessment > 2]

def getKey(json, key):
  return json.get(key, False)

def JSONToPlayerFlags(json):
  return PlayerFlags(getKey(json, 'ser'),
    getKey(json, 'aha'),
    getKey(json, 'hbr'),
    getKey(json, 'mbr'),
    getKey(json, 'cmt'),
    getKey(json, 'nfm'),
    getKey(json, 'sha'))

def JSONToPlayerAssessment(json):
  try:
    return PlayerAssessment(
      json['_id'],
      json['gameId'],
      json['userId'],
      json['white'],
      json['assessment'],
      json['date'],
      json['sfAvg'],
      json['sfSd'],
      json['mtAvg'],
      json['mtSd'],
      json['blurs'],
      json['hold'],
      JSONToPlayerFlags(json['flags']))
  except KeyError:
    return None

class PlayerAssessmentDB:
  def __init__(self, playerAssessmentColl):
    self.playerAssessmentColl = playerAssessmentColl

  def byId(self, _id): # string
    try:
      return JSONToPlayerAssessment(self.playerAssessmentColl.find_one({'_id': _id}))
    except:
      return None

  def byIds(self, ids): # List[String]
    return PlayerAssessments(list([JSONToPlayerAssessment(pa) for pa in self.playerAssessmentColl.find({'_id': {'$in': list([i for i in ids])}})]))

  def byUserId(self, userId):
    return PlayerAssessments(list([JSONToPlayerAssessment(pa) for pa in self.playerAssessmentColl.find({'userId': userId})]))

  def byGameId(self, gameId):
    try:
      return JSONToPlayerAssessment(self.playerAssessmentColl.find_one({'gameId': gameId}))
    except:
      return None

  def byGameIds(self, gameIds):
    return PlayerAssessments(JSONToPlayerAssessment(self.playerAssessmentColl.find({'gameId': {'$in': gameId}})))

  def write(self, playerAssessment):
    self.playerAssessmentColl.update_one({'_id': playerAssessment.id}, {'$set': playerAssessment.json()}, upsert=True)

  def writeMany(self, playerAssessments):
    if len(playerAssessments.playerAssessments) > 0:
      self.playerAssessmentColl.insert_many(list([pa.json for pa in playerAssessments.playerAssessments]))

  def lazyWriteMany(self, playerAssessments):
    [self.write(pa) for pa in playerAssessments.playerAssessments]