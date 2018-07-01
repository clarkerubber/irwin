from collections import namedtuple

class Queue(namedtuple('Queue', ['env'])):
	def nextDeepAnalysis(self, token):
		return self.env.deepPlayerQueueDB.nextUnprocessed(token.id)

	def completeDeepAnalysis(self, _id):
		return self.env.deepPlayerQueueDB.updateComplete(_id, complete=True)

