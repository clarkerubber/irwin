import logging

from collections import namedtuple

from modules.game.AnalysedGame import AnalysedGameBSONHandler

class Api(namedtuple('Api', ['env'])):
	def insertAnalysedGames(self, analysedGamesBSON):
		try:
			analysedGames = [AnalysedGameBSONHandler.reads(g) for g in analysedGamesBSON]
			env.analysedGameDB.lazyWriteMany(analysedGames)
		except KeyError, ValueError:
			logging.warning('Malformed analysedGamesBSON: ' + str(analysedGamesBSON))