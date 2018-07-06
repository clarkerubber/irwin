from default_imports import *

from modules.game.Colour import Colour

@validated
class EngineEval(NamedTuple('EngineEval', [
        ('cp', Opt[Number]),
        ('mate', Opt[int])
    ])):
    @staticmethod
    @validated
    def fromDict(d: Dict) -> EngineEval:
        return EngineEval(d.get('cp', None), d.get('mate', None))

    @validated
    def asdict(self) -> Dict:
        return {'cp': self.cp} if self.cp is not None else {'mate': self.mate}

    @validated
    def inverse(self) -> EngineEval:
        return EngineEval(-self.cp if self.cp is not None else None,
            -self.mate if self.mate is not None else None)

    @validated
    def winningChances(self, colour: Colour) -> Number:
        if self.mate is not None:
            base = (1 if self.mate > 0 else 0)
        else:
            base = 1 / (1 + math.exp(-0.004 * self.cp))
        return 100*(base if colour else (1-base))

class EngineEvalBSONHandler:
    @staticmethod
    @validated
    def reads(bson: Dict) -> List[EngineEval]:
        return EngineEval.fromDict(bson)

    @validated
    def writes(engineEval: EngineEval) -> Dict:
        return engineEval.asdict()