from default_imports import *

from modules.queue.Env import Env
from modules.queue.EngineQueue import EngineQueue, EngineQueueID

from modules.auth.Auth import Authable

class Queue(NamedTuple('Queue', [('env', Env)])):
    def nextEngineAnalysis(self, id: EngineQueueID) -> EngineQueue:
        return self.env.engineQueueDB.nextUnprocessed(id)

    def completeEngineAnalysis(self, _id: EngineQueueID):
        return self.env.engineQueueDB.updateComplete(_id, complete=True)

    def nextIrwinAnalysis(self):
        return None
        #return self.env.irwinAnalysisQueueDB.