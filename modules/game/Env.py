from modules.game.Game import GameDB
from modules.game.AnalysedGame import AnalysedGameDB
from modules.game.Player import PlayerDB
from modules.game.AnalysedPosition import AnalysedPositionDB

class Env:
	def __init__(self, settings, db):
		gameDB = GameDB(db[settings['game']['coll']['game']])
		analysedGameDB = AnalysedGameDB(db[settings['game']['coll']['game_analysis']])
		playerDB = PlayerDB(db['game']['coll']['player'])
		analysedPositionDB = AnalysedPositionDB(db['game']['coll']['position_analysis'])