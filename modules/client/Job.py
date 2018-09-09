from default_imports import *

from modules.game.Player import PlayerID
from modules.game.Game import Game, GameBSONHandler
from modules.game.AnalysedPosition import AnalysedPosition, AnalysedPositionBSONHandler

class Job(NamedTuple('Job', [
        ('playerId', PlayerID),
        ('games', List[Game]),
        ('analysedPositions', List[AnalysedPosition])
    ])):
    @staticmethod
    def fromJson(json: Dict):
        try:
            return JobBSONHandler.reads(json)
        except KeyError as e:
            logging.warning(f'Failed convert {json} to Job: {e}')
            return None

    def toJson(self):
        return JobBSONHandler.writes(self)

class JobBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Job:
        return Job(
            playerId = bson['playerId'],
            games = [GameBSONHandler.reads(g) for g in bson['games']],
            analysedPositions = [AnalysedPositionBSONHandler.reads(ap) for ap in bson['analysedPositions']])

    @staticmethod
    def writes(job: Job) -> Dict:
        return {
            'playerId': job.playerId,
            'games': [GameBSONHandler.writes(g) for g in job.games],
            'analysedPositions': [AnalysedPositionBSONHandler.writes(ap) for ap in job.analysedPositions]
        }