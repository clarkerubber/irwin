from defaul_imports import *

Permission = NewType('Permission', str)

Priv = validated(NamedTuple('Priv' [
        ('permission', Permission)
    ]))

class PrivBSONHandler:
	@staticmethod
    @validated
	def reads(bson: Dict) -> Priv:
		return Priv(
			permission=bson['_id'])

	@staticmethod
    @validated
	def writes(priv: Priv) -> Dict:
		return {
			'_id': priv.permission}