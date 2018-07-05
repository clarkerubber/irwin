from collections import namedtuple

class Blurs(namedtuple('Blurs', ['nb', 'moves'])):
    @staticmethod
    def fromDict(d, l):
        """
        d: Dict (game data)
        l: Int (amount of plys played by player)
        """
        moves = [i == '1' for i in list(d.get('bits', ''))]
        moves += [False] * (l - len(moves))
        return Blurs(
            nb = d.get('nb', 0),
            moves = moves
        )

class BlursBSONHandler:
    @staticmethod
    def reads(bson):
        return Blurs(
            nb = bson['nb'],
            moves = [i == 1 for i in list(bson['bits'])]
            )
    def writes(blurs):
        return {
            'nb': blurs.nb,
            'bits': ''.join(['1' if i else '0' for i in blurs.moves])
        }