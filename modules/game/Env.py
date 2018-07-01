from modules.game.Game import GameDB
from modules.game.GameAnalysis import GameAnalysisDB
from modules.game.Player import PlayerDB
from modules.game.PositionAnalysis import PositionAnalysisDB

class Env:
	def __init__(self, settings, db):
		gameDB = GameDB(db[settings['game']['coll']['game']])
		gameAnalysisDB = GameAnalysisDB(db[settings['game']['coll']['game_analysis']])
		playerDB = PlayerDB(db['game']['coll']['player'])
		positionAnalysisDB = PositionAnalysisDB(db['game']['coll']['position_analysis'])