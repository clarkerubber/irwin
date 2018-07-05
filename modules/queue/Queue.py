from collections import namedtuple

class Queue(namedtuple('Queue', ['env'])):
	def nextEngineAnalysis(self, token):
		return self.env.engineAnalysisQueueDB.nextUnprocessed(token.id)

	def completeEngineAnalysis(self, _id):
		return self.env.engineAnalysisQueueDB.updateComplete(_id, complete=True)

	def nextIrwinAnalysis(self):
		return self.env.irwinAnalysisQueueDB.