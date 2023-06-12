from dataclasses import dataclass
from enum import Enum
from typing import List


@dataclass
class Player:
    ID: int = -1
    profileID: str = None
    username: str = None
    teamIndex: int = -1
    operator: int = -1
    heroName: int = -1
    alliance: int = -1
    roleImage: int = -1
    roleName: str = None
    rolePortrait: int = -1
    spawn: str = None
    id: bytes = None

@dataclass
class Team:
    name: str = None
    score: int = -1
    won: bool = False
    winCondition: str = None
    role: str = None

@dataclass
class Header:
    gameVer: str = None
    codeVer: str = None
    timestamp: str = None
    matchType: int = -1
    map: int = -1
    site: str = None
    recordingPlayerID: int = -1
    recordingProfileID: str = None
    additionalTags: str = None
    gameMode: int = -1
    roundsPerMatch: int = -1
    roundsPerMatchOT: int = -1
    roundNumber: int = -1
    OTRoundNumber: int = -1
    teams: List[Team] = None
    players: List[Player] = None
    gmSettings: list = None
    playlistCategory: int = -1
    matchID: str = None


MatchUpdateType = Enum("MatchUpdateType", "Kill Death DefuserPlantStart DefuserPlantComplete DefuserDisableStart DefuserDisableComplete LocatedObjective OperatorSwap Battleye PlayerLeave Other")


@dataclass
class MatchUpdate:
    type: MatchUpdateType = None
    username: str = None
    target: str = None
    headshot: bool = False
    time: str = None
    timeInSeconds: float = -1
    message: str = None
    operator: int = -1
