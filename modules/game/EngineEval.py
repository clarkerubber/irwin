from collections import namedtuple

class EngineEval(namedtuple('EngineEval', ['cp', 'mate'])):
    @staticmethod
    def fromDict(d):
        return EngineEval(d.get('cp', None), d.get('mate', None))

    def toDict(self):
        return {'cp': self.cp} if self.cp is not None else {'mate': self.mate}

    def winningChances(self, white):
        if self.mate is not None:
            base = (1 if self.mate > 0 else 0)
        else:
            base = 1 / (1 + math.exp(-0.004 * self.cp))
        return 100*(base if white else (1-base))

class EngineEvalBSONHandler:
    @staticmethod
    def reads(bson):
        return [EngineEval.fromDict(s) for s in bson]

    def writes(engineEvals):
        return [s.toDict() for s in engineEvals]