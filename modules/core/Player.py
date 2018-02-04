from collections import namedtuple

class Player(namedtuple('Player', ['id', 'titled', 'engine', 'gamesPlayed', 'closedReports'])):
    def setEngine(self, status):
        return Player(
            id=self.id,
            titled=self.titled,
            engine=status,
            gamesPlayed=self.gamesPlayed,
            closedReports=self.closedReports)

    @staticmethod
    def fromPlayerData(data):
        user = data.get('user')
        if user is not None:
            return Player(
                id=user.get('id'),
                titled=user.get('title') is not None,
                engine=user.get('engine') is not None,
                gamesPlayed=sum([d.get('games', 0) for perf, d in user.get('perfs', {}).items()]),
                closedReports=len(data.get('assessment', {}).get('relatedCheaters', [])))
        return None

class PlayerBSONHandler:
    @staticmethod
    def reads(bson):
        return Player(
                id = bson['_id'],
                titled = bson.get('titled', False),
                engine = bson['engine'],
                gamesPlayed = bson['gamesPlayed'],
                closedReports = bson['closedReports']
            )

    def writes(player):
        return {
            '_id': player.id,
            'titled': player.titled,
            'engine': player.engine,
            'gamesPlayed': player.gamesPlayed,
            'closedReports': player.closedReports
        }

class PlayerDB(namedtuple('PlayerDB', ['playerColl'])):
    def byId(self, _id):
        playerBSON = self.playerColl.find_one({'_id': _id})
        return None if playerBSON is None else PlayerBSONHandler.reads(playerBSON)

    def balancedSample(self, size):
        pipelines = [[
                {"$match": {"engine": True}},
                {"$sample": {"size": int(size/2)}}
            ],[
                {"$match": {"engine": False}},
                {"$sample": {"size": int(size/2)}}
            ]]
        engines = [PlayerBSONHandler.reads(p) for p in self.playerColl.aggregate(pipelines[0])]
        legits = [PlayerBSONHandler.reads(p) for p in self.playerColl.aggregate(pipelines[1])]
        return engines + legits

    def byEngine(self, engine):
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({'engine': engine})]

    def all(self):
        return [PlayerBSONHandler.reads(p) for p in self.playerColl.find({})]

    def write(self, player):
        self.playerColl.update_one({'_id': player.id}, {'$set': PlayerBSONHandler.writes(player)}, upsert=True)