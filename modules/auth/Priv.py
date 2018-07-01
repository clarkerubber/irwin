from collections import namedtuple

Priv = namedtuple('Priv', ['id', 'permission'])

class PrivBSONHandler:
	@staticmethod
	def reads(bson):
		return Priv(
			id=bson['_id'],
			permission=bson['permission'])

	@staticmethod
	def writes(priv):
		return {
			'_id': priv.id,
			'permission': priv.permission}