# File: t (Python 2.4)

from otp.level.EntityTypes import *

class CogdoLevelMgr(LevelMgr):
    type = 'levelMgr'


class CogdoBoardroomGameSettings(Entity):
    type = 'cogdoBoardroomGameSettings'
    attribs = (('TimerScale', 1.0, 'float'),)


class CogdoCraneGameSettings(Entity):
    type = 'cogdoCraneGameSettings'
    attribs = (('GameDuration', 180.0, 'float'), ('EmptyFrictionCoef', 0.10000000000000001, 'float'), ('Gravity', -32, 'int'), ('RopeLinkMass', 1.0, 'float'), ('MagnetMass', 1.0, 'float'), ('MoneyBagGrabHeight', -8.1999999999999993, 'float'))


class CogdoCraneCogSettings(Entity):
    type = 'cogdoCraneCogSettings'
    attribs = (('CogSpawnPeriod', 10.0, 'float'), ('CogWalkSpeed', 2.0, 'float'), ('CogMachineInteractDuration', 2.0, 'float'), ('CogFlyAwayHeight', 50.0, 'float'), ('CogFlyAwayDuration', 4.0, 'float'))

