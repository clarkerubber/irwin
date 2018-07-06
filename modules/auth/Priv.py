from defaul_imports import *

Permission = NewType('Permission', str)

Priv = validated(NamedTuple('Priv' [
        ('permission', Permission)
    ]))

RequestJob = Priv('request_job') # client can request work
CompleteJob = Priv('complete_job') # client can post results of work
PostJob = Priv('post_job') # lichess can post a job for analysis

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