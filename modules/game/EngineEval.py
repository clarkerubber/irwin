from default_imports import *

from modules.game.Colour import Colour

class EngineEval(NamedTuple('EngineEval', [
        ('cp', Opt[Number]),
        ('mate', Opt[int])
    ])):
    @staticmethod
    def fromDict(d: Dict):
        return EngineEval(d.get('cp', None), d.get('mate', None))

    def asdict(self) -> Dict:
        return {'cp': self.cp} if self.cp is not None else {'mate': self.mate}

    def inverse(self):
        return EngineEval(-self.cp if self.cp is not None else None,
            -self.mate if self.mate is not None else None)

    def winningChances(self, colour: Colour) -> Number:
        if self.mate is not None:
            base = (1 if self.mate > 0 else 0)
        else:
            base = 1 / (1 + math.exp(-0.004 * self.cp))
        return 100*(base if colour else (1-base))

class EngineEvalBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> List[EngineEval]:
        return EngineEval.fromDict(bson)

    def writes(engineEval: EngineEval) -> Dict:
        return engineEval.asdict()