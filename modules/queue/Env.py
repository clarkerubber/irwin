from default_imports import *

from conf.ConfigWrapper import ConfigWrapper

from pymongo.collection import Collection

from modules.queue.EngineQueue import EngineQueueDB
from modules.queue.IrwinQueue import IrwinQueueDB

class Env:
    	def __init__(self, config: ConfigWrapper, db: Collection):
		self.db = db

		self.engineQueueDB = EngineQueueDB(db[config['queue coll engine_queue']])
		self.irwinQueueDB = IrwinQueueDB(db[config['queue coll irwin_queue']])