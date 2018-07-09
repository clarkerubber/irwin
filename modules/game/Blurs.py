from default_imports import *

class Blurs(NamedTuple('Blurs', [
        ('nb', int),
        ('moves', List[bool])
    ])):
    """
    The blurs for a single side in a Game
    """
    @staticmethod
    def fromDict(d: Dict, l: int):
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
    def reads(bson: Dict) -> Blurs:
        moves = [i == '1' for i in list(bson['bits'])]
        return Blurs(
            nb = sum(moves),
            moves = moves
            )

    @staticmethod
    def writes(blurs: Blurs) -> Dict:
        return {
            'bits': ''.join(['1' if i else '0' for i in blurs.moves])
        }