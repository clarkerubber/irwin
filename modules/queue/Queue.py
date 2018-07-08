from default_imports import *

from modules.queue.Env import Env
from modules.queue.EngineQueue import EngineQueueID

from modules.auth.Auth import Authable

class Queue(NamedTuple('Queue', [('env', Env)])):
    	def nextEngineAnalysis(self, authable: Authable):
		return self.env.engineAnalysisQueueDB.nextUnprocessed(authable.id)

    	def completeEngineAnalysis(self, _id: EngineQueueID):
		return self.env.engineAnalysisQueueDB.updateComplete(_id, complete=True)

    	def nextIrwinAnalysis(self):
		return self.env.irwinAnalysisQueueDB.