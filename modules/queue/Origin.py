from default_imports import *

Origin = NewType('Origin', str)
OriginReport = Origin('report')
OriginModerator = Origin('moderator')
OriginRandom = Origin('random')