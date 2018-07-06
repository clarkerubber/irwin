from default_imports import *

@validated
class Blurs(NamedTuple('Blurs', [
        ('nb', int),
        ('moves', List[bool])
    ])):
    """
    The blurs for a single side in a Game
    """
    @staticmethod
    @validated
    def fromDict(d: Dict, l: int) -> Blurs:
        """
        d being from game data
        l being the amount of plys played by the player
        """
        moves = [i == '1' for i in list(d.get('bits', ''))]
        moves += [False] * (l - len(moves))
        return Blurs(
            nb = d.get('nb', 0),
            moves = moves
        )

class BlursBSONHandler:
    @staticmethod
    @validated
    def reads(bson: Dict) -> Blurs:
        return Blurs(
            nb = sum(list(bson['bits'])),
            moves = [i == 1 for i in list(bson['bits'])]
            )

    @staticmethod
    @validated
    def writes(blurs: Blurs) -> Dict:
        return {
            'bits': ''.join(['1' if i else '0' for i in blurs.moves])
        }