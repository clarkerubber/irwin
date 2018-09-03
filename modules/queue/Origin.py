from default_imports import *

Origin = NewType('Origin', str)
OriginReport = Origin('report')
OriginModerator = Origin('moderator')
OriginRandom = Origin('random')

def maxOrigin(a, b):
    if a == OriginModerator or b == OriginModerator:
        return OriginModerator

    if a == OriginReport or b == OriginReport:
        return OriginReport

    return OriginRandom