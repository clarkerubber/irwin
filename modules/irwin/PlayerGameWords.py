from collections import namedtuple
import datetime
import pymongo

PlayerGameWords = namedtuple('PlayerGameWords', ['generalGameWords', 'narrowGameWords', 'generalPositionWords', 'narrowPositionWords'])

class PlayerGameWordsBSONHandler:
  @staticmethod
  def reads(bson):
    return PlayerGameWords(
      generalGameWords = bson['generalGameWords'],
      narrowGameWords = bson['narrowGameWords'],
      generalPositionWords = bson['generalPositionWords'],
      narrowPositionWords = bson['narrowPositionWords'])

  @staticmethod
  def writes(PlayerGameWords):
    return {
      'date': datetime.datetime.utcnow(),
      'generalGameWords': PlayerGameWords.generalGameWords,
      'narrowGameWords': PlayerGameWords.narrowGameWords,
      'generalPositionWords': PlayerGameWords.generalPositionWords,
      'narrowPositionWords': PlayerGameWords.narrowPositionWords
    }

class PlayerGameWordsDB(namedtuple('PlayerGameWordsDB', ['playerGameWordsColl'])):
  def write(self, playerGameWords):
    self.playerGameWordsColl.insert_one(PlayerGameWordsBSONHandler.writes(playerGameWords))

  def newest(self):
    return PlayerGameWordsBSONHandler.reads(self.playerGameWordsColl.find_one(sort=[("date", pymongo.DESCENDING)]))