from bson.objectid import ObjectId

class PlayerAssessment:
    def __init__(self, jsonin):
        self.json = jsonin
        self.id = jsonin['_id']
        self.gameId = jsonin['gameId']
        self.userId = jsonin['userId']
        self.white = jsonin['white']
        self.assessment = jsonin['assessment']
        self.date = jsonin['date']
        self.sfAvg = jsonin['sfAvg']
        self.sfSd = jsonin['sfSd']
        self.mtAvg = jsonin['mtAvg']
        self.mtSd = jsonin['mtSd']
        self.blurs = jsonin['blurs'] # percentage 0-100 blur rate
        self.hold = jsonin['hold'] # boolean hold alert
        self.flags = PlayerFlags(jsonin['flags'])

    def __str__(self):
      return str(self.json)

class PlayerFlags:
    def __init__(self, jsonin):
        self.jsonin = jsonin
        self.ser = self.get_key('ser') # Suspicious Error Rate
        self.aha = self.get_key('aha') # Always Has Advantage
        self.hbr = self.get_key('hbr') # High Blur Rate
        self.mbr = self.get_key('mbr') # Medium Blur Rate
        self.cmt = self.get_key('cmt') # Consistent Move Times
        self.nfm = self.get_key('nfm') # No Fast Moves
        self.sha = self.get_key('sha') # Suspicious Hold Alert

    def get_key(self, key):
        return self.jsonin.get(key, False)

class PlayerAssessments:
  def __init__(self, playerAssessments):
    self.playerAssessments = playerAssessments # Raw JSON input
    self.list = [PlayerAssessment(p) for p in playerAssessments] # List[PlayerAssessment]

  def __str__(self):
    return str([str(pa) for pa in self.list])

  def byGameIds(self, gameIds):
    return [p for p in self.list if p.gameId in gameIds]

  def byGameId(self, gameId):
    return next(iter([p for p in self.list if p.gameId == gameId]), None)

  def suspicious(self):
    return [p for p in self.list if p.assessment > 2]

class PlayerAssessmentDB:
  def __init__(self, assessColl):
    self.assessColl = assessColl

  def byId(self, _id): # string
    try:
      return PlayerAssessment(self.assessColl.find_one({'_id': ObjectId(_id)}))
    except:
      return None

  def byIds(self, ids): # List[String]
    return PlayerAssessments(self.assessColl.find({'_id': {'$in': list([ObjectId(i) for i in ids])}}))

  def byUserId(self, userId):
    return PlayerAssessments(self.assessColl.find({'userId': userId}))

  def byGameId(self, gameId):
    try:
      return PlayerAssessment(self.assessColl.find_one({'gameId': gameId}))
    except:
      return None

  def byGameIds(self, gameIds):
    return PlayerAssessments(self.assessColl.find({'gameId': {'$in': gameId}}))

  def write(self, playerAssessment):
    self.assessColl.update_one({'_id': playerAssessment.json['_id']}, {'$set': playerAssessment.json}, upsert=True)

  def writeMany(self, playerAssessments):
    if len(playerAssessments.list) > 0:
      self.assessColl.insert_many(list([pa.json for pa in playerAssessments.list]))

  def lazyWriteMany(self, playerAssessments):
    [self.write(pa) for pa in playerAssessments.list]