import pandas as pd
from ReplayParser.DataClasses import Header, MatchUpdate, MatchUpdateType as MUT
from typing import List
import ReplayParser.IDDecoding as Decode
from ReplayParser.Reader import Reader
from dataclasses import dataclass
from copy import deepcopy
import os
import time
from pathlib import Path
import ntpath
import pandasql as ps


@dataclass
class PlayerRoundInfo:
    name: str = None
    operator: str = None
    kills: int = 0
    headshots: int = 0
    pivotKills: int = 0
    untradedKills: int = 0
    died: bool = False
    pivotDeath: bool = False
    openingKill = False
    openingDeath = False
    objective: bool = False
    traded: bool = False
    role: str = None
    spawn: str = None           # This can be wrong for attackers if they change spawn (I think?)


@dataclass
class TeamRoundInfo:
    role: str = None
    score: int = -1
    won: bool = False
    winCondition: str = None
    players: List[PlayerRoundInfo] = None


@dataclass
class RoundHeader:
    matchID: str = None
    map: str = None
    site: str = None
    roundNum: int = -1
    attackers: TeamRoundInfo = None
    defenders: TeamRoundInfo = None
    allPlayers: List[PlayerRoundInfo] = None


def convertPlayerNameToAlias(name, aliasDict):
    if aliasDict is None:
        return name

    aliasDict = convertPlayerDict(aliasDict)

    try:
        return aliasDict[name]
    except KeyError:
        return name


# Takes in header and event info from the Reader
def processRound(roundHeader: Header, events: List[MatchUpdate], aliasDict=None):

    newHeader = RoundHeader()                   # Naming is a bit confusing, might make differences clear later
    newHeader.matchID = roundHeader.matchID
    newHeader.map = Decode.getMapName(roundHeader.map)
    newHeader.site = roundHeader.site
    newHeader.roundNum = roundHeader.roundNumber

    newHeader.attackers = TeamRoundInfo()
    newHeader.defenders = TeamRoundInfo()

    attackData, attackIndex = getTeamByRole(roundHeader, True)
    defenseData, defenseIndex = getTeamByRole(roundHeader, False)
    
    newHeader.attackers.role = "Attack"
    newHeader.attackers.won = attackData.won
    newHeader.attackers.winCondition = attackData.winCondition
    newHeader.attackers.score = attackData.score
    newHeader.attackers.players = []

    newHeader.defenders.role = "Defense"
    newHeader.defenders.won = defenseData.won
    newHeader.defenders.winCondition = defenseData.winCondition
    newHeader.defenders.score = defenseData.score
    newHeader.defenders.players = []

    players = []
    for p in roundHeader.players:
        newPlayer = PlayerRoundInfo()
        newPlayer.name = convertPlayerNameToAlias(p.username, aliasDict)
        newPlayer.operator = Decode.getOpName(p.operator)
        newPlayer.role = ("Attack" if p.teamIndex == attackIndex else "Defense")
        newPlayer.spawn = p.spawn

        players.append(newPlayer)
        if newPlayer.role == "Attack":
            newHeader.attackers.players.append(newPlayer)
        else:
            newHeader.defenders.players.append(newPlayer)

    newHeader.allPlayers = players

    processedEvents = processEventFeed(events, newHeader, aliasDict=aliasDict)
    calculatePlayerRoundStats(processedEvents, newHeader, aliasDict=aliasDict)

    return newHeader


def getTeamByRole(roundHeader: Header, isAttack):
    i = 0
    for t in roundHeader.teams:
        if t.role == ("Attack" if isAttack else "Defense"):
            return t, i
        i += 1
    
    return None


def getPlayer(header: RoundHeader, playerName: str, aliasDict=None):
    alias = convertPlayerNameToAlias(playerName, aliasDict)
    for p in header.allPlayers:
        if p.name == alias:
            return p
    print("Player with name \"" + playerName + "\" not found")
    return None


def processEventFeed(eventFeed: List[MatchUpdate], header: RoundHeader, aliasDict=None):
    processedEvents = []
    inPrep = True
    postPlant = False
    plantStartTime = -1.0

    # Process each event in order based on the event type
    for e in eventFeed:
        if e.type == MUT.OperatorSwap:
            p = getPlayer(header, e.username, aliasDict)
            p.operator = Decode.getOpName(e.operator)

        # This marks the start of the action phase
        if (e.type == MUT.Other) and (e.timeInSeconds >= 170) and inPrep:
            inPrep = False

        # We don't need any special processing for these
        if e.type in [MUT.Kill, MUT.Death, MUT.DefuserDisableStart]:
            processedEvents.append(deepcopy(e))

        # We save the plant start time so that we can calculate the plant end time later
        if e.type == MUT.DefuserPlantStart:
            plantStartTime = e.timeInSeconds
            processedEvents.append(deepcopy(e))

        # This marks the shift to the post-plant period
        if e.type == MUT.DefuserPlantComplete:
            # The time stamp for this event is always 0.0 iirc
            # (might not be, but either way this should give the same value)
            plantEndTime = max(0.0, plantStartTime - 7.0)
            # We need to shift every event we recorded so far to a relative time based on the post-plant period
            for pe in processedEvents:
                pe.timeInSeconds = pe.timeInSeconds - plantEndTime + 45.0

            # This isn't used but it might be useful with future updates, so I'm leaving it
            postPlant = True
            processedEvents.append(deepcopy(e))

        # Marks an end game condition
        if e.type == MUT.DefuserDisableComplete:
            processedEvents.append(deepcopy(e))
            break

    return processedEvents


def getPlayerTeam(header: RoundHeader, playerName: str, aliasDict=None):
    p = getPlayer(header, playerName, aliasDict)
    return p.role


def calculatePlayerRoundStats(processedEvents: List[MatchUpdate], header: RoundHeader, tradeWindow=8.0, aliasDict=None):
    openerTime = -1.0
    killsToBeTraded = []
    potentialPivotKills = []
    playerDelta = 0         # Attacker count - Defender count

    for e in processedEvents:
        if e.type in [MUT.DefuserPlantComplete, MUT.DefuserDisableComplete]:
            p = getPlayer(header, e.username, aliasDict)
            p.objective = True

        if e.type == MUT.Death:
            p = getPlayer(header, e.username, aliasDict)
            p.died = True
            if e.timeInSeconds >= openerTime:
                openerTime = e.timeInSeconds
                p.openingDeath = True

            deltaDir = -1 if p.role == "Attack" else 1
            playerDelta += deltaDir

            if (playerDelta == 0) or (playerDelta == deltaDir):
                p.pivotDeath = True
                processPivots(potentialPivotKills, header, aliasDict)
                potentialPivotKills = []

            if ((p.role == "Attack") and (playerDelta < -1)) or ((p.role == "Defense") and (playerDelta > 1)):
                potentialPivotKills.append(e)

        if e.type == MUT.Kill:
            p = getPlayer(header, e.username, aliasDict)
            p2 = getPlayer(header, e.target, aliasDict)

            if p.role != p2.role:
                p.kills += 1
                killsToBeTraded.append(e)
                if e.headshot:
                    p.headshots += 1

            p2.died = True

            if e.timeInSeconds > openerTime:
                openerTime = e.timeInSeconds
                if p.role != p2.role:
                    p.openingKill = True
                p2.openingDeath = True

            deltaDir = 1 if p2.role == "Defense" else -1
            playerDelta += deltaDir

            if (playerDelta == 0) or (playerDelta == deltaDir):
                potentialPivotKills.append(e)
                processPivots(potentialPivotKills, header, aliasDict)
                potentialPivotKills = []

            if ((p2.role == "Defense") and (playerDelta > 1)) or ((p2.role == "Attack") and (playerDelta < -1)):
                potentialPivotKills.append(e)

            for i in range(len(killsToBeTraded) - 1, -1, -1):
                k = killsToBeTraded[i]
                if k.timeInSeconds - e.timeInSeconds <= tradeWindow:
                    if k.username == e.target:
                        p3 = getPlayer(header, k.target, aliasDict)
                        p3.traded = True

                        p4 = getPlayer(header, k.username, aliasDict)
                        p4.untradedKills -= 1
                else:
                    # Out of trade window, don't need to process it anymore
                    del killsToBeTraded[i]

    for p in header.allPlayers:
        p.untradedKills += p.kills


def processPivots(pivots: List[MatchUpdate], header: RoundHeader, aliasDict=None):
    for e in pivots:
        if e.type == MUT.Death:
            p = getPlayer(header, e.username, aliasDict)
            p.pivotDeath = True
        if e.type == MUT.Kill:
            p = getPlayer(header, e.username, aliasDict)
            p2 = getPlayer(header, e.target, aliasDict)

            if p.role != p2.role:
                p.pivotKills += 1

            p2.pivotDeath = True


def convertPlayerDict(playerDict):
    reverseDict = {}
    for playerName in playerDict.keys():
        aliases = playerDict[playerName]
        for alias in aliases:
            reverseDict[alias] = playerName

    return reverseDict


# This function expects all the files in the given folder to be .rec files
# Basically just patch a match folder in and it should work
def processMatch(folderPath, playersToCareAbout: dict, parserVerbose=False):

    startTime = time.time()
    roundInfos: List[RoundHeader] = []

    aliasList = list(playersToCareAbout.keys())

    for file in os.listdir(folderPath):
        if file.endswith(".rec"):
            roundFilePath = folderPath + "\\" + file
            roundParser = Reader(roundFilePath)
            roundParser.read(verbose=parserVerbose)
            if roundParser.roundEnded:
                roundData = processRound(roundParser.header, roundParser.matchFeedback, aliasDict=playersToCareAbout)
                roundInfos.append(roundData)
                print("Processed Round", roundInfos[-1].roundNum)
                print()
            else:
                print("Round", roundParser.header.roundNumber, "did not end properly")

    roundTable, playerTable = matchDataToTable(roundInfos, aliasList)
    matchName = ntpath.basename(folderPath)
    save(roundTable, playerTable, matchName)

    endTime = time.time()
    timeStr = time.strftime('%H:%M:%S', time.gmtime(endTime - startTime))
    print("Total time to process match:", timeStr)


# This function expects the input to be a folder of matches (which themselves should be a folder of .rec files)
def processMultipleMatches(folderPath, saveName, playersToCareAbout: dict, parserVerbose=False):
    startTime = time.time()
    roundInfos: List[RoundHeader] = []
    numMatches = 0

    aliasList = list(playersToCareAbout.keys())

    for matchName in os.listdir(folderPath):
        matchPath = folderPath + "\\" + matchName
        print("Processing Match", matchName)
        containsReplay = False
        for file in os.listdir(matchPath):
            if file.endswith(".rec"):
                containsReplay = True
                roundFilePath = matchPath + "\\" + file
                roundParser = Reader(roundFilePath)
                roundParser.read(verbose=parserVerbose)
                if roundParser.roundEnded:
                    roundData = processRound(roundParser.header, roundParser.matchFeedback, aliasDict=playersToCareAbout)
                    roundInfos.append(roundData)
                    print("\tRound", roundInfos[-1].roundNum)
                    print()
                else:
                    print("\tRound", roundParser.header.roundNumber, "did not end properly")
        if containsReplay:
            numMatches += 1
        print("Finished processing Match", matchName)

    roundTable, playerTable = matchDataToTable(roundInfos, aliasList)
    save(roundTable, playerTable, saveName)

    endTime = time.time()
    timeStr = time.strftime('%H:%M:%S', time.gmtime(endTime - startTime))
    print("Total time to process all", numMatches, "matches:", timeStr)


# Note: ALL players must be on the same team
# I will cry otherwise
# If you want to record data for players on both teams, call this twice
# Note: You can call this on multiple matches, it doesn't really matter since the match info is stored in the round header
def matchDataToTable(matchData: List[RoundHeader], playerNames: List[str]):

    roundTable = pd.DataFrame(columns=["Match ID", "Round", "Map", "Site", "Attack/Defense", "Planted", "Disabled", "Win/Loss", "Win Condition"])
    playerTable = pd.DataFrame(columns=["Name", "Match ID", "Round", "Operator", "Spawn", "Kills", "Headshots", "Pivot Kills", "Untraded Kills", "Died", "Pivot Death", "Opening Kill", "Opening Death", "Objective Play", "Traded"])

    for roundData in matchData:
        matchID = roundData.matchID
        roundNum = roundData.attackers.score + roundData.defenders.score

        playersToCareAbout = [getPlayer(roundData, pName) for pName in playerNames]
        playersToCareAbout = [p for p in playersToCareAbout if p is not None]
        playerTeams = [p.role for p in playersToCareAbout]
        if not (playerTeams.count(playerTeams[0]) == len(playerTeams)):
            raise Exception("All players to be analyzed must be on the same team")

        teamToCareAbout = playerTeams[0]

        winLoss = "?"
        winCondition = "?"
        if roundData.attackers.winCondition is not None:
            winLoss = "Win" if teamToCareAbout == "Attack" else "Loss"
            winCondition = roundData.attackers.winCondition

        if roundData.defenders.winCondition is not None:
            winLoss = "Win" if teamToCareAbout == "Defense" else "Loss"
            winCondition = roundData.defenders.winCondition

        planted = False
        disabled = False

        for p in roundData.allPlayers:
            if p.objective:
                if p.role == "Attack":
                    planted = True
                elif p.role == "Defense":
                    disabled = True

            if p in playersToCareAbout:
                playerRow = [p.name, matchID, roundNum, p.operator, p.spawn, p.kills, p.headshots, p.pivotKills,
                              p.untradedKills, p.died, p.pivotDeath, p.openingKill, p.openingDeath, p.objective, p.traded]
                playerTable.loc[len(playerTable)] = playerRow

        roundRow = [matchID, roundNum, roundData.map, roundData.site, teamToCareAbout, planted, disabled, winLoss, winCondition]
        roundTable.loc[len(roundTable)] = roundRow

    return roundTable, playerTable


def save(roundTable, playerTable, fileName):
    outputPath = str(Path(__file__).parent.parent) + "\\Output\\" + fileName + "_Stats.xlsx"
    writer = pd.ExcelWriter(outputPath)

    roundTable.to_excel(writer, sheet_name="Rounds", index=False)
    playerTable.to_excel(writer, sheet_name="Players", index=False)

    writer.close()


def compileStats(fileName, perMatch=False):
    ioPath = str(Path(__file__).parent.parent) + "\\Output\\" + fileName + "_Stats.xlsx"

    roundTable = pd.read_excel(ioPath, sheet_name="Rounds")
    playerTable = pd.read_excel(ioPath, sheet_name="Players")

    keyStr = "Name"
    if perMatch:
        keyStr = keyStr + ", \"Match ID\""

    aggregated = ps.sqldf(
            "select " +
            keyStr +
            ", sum(Kills) as Kills, sum(Died) as Deaths, sum(Headshots) * 100.0 /sum(Kills) as \"Headshot %\", " +
            "sum(\"Pivot Kills\") as \"Pivot Kills\", sum(\"Pivot Death\") as \"Pivot Deaths\", " +
            "sum(\"Opening Kill\") as \"Opening Kills\", sum(\"Opening Death\") as \"Opening Deaths\", " +
            "sum(\"Untraded Kills\") as \"Untraded Kills\", sum(Died) - sum(Traded) as \"Untraded Deaths\", " +
            "sum(case when Kills > 0 or \"Objective Play\" or not Died or Traded then 1 else 0 end) * 1.0 / count(*) as KOST " +
            "from playerTable group by " +
            keyStr
    )

    combinedStats = ps.sqldf(
        "select (case when Deaths=0 then Kills else Kills* 1.0 /Deaths end) as KD, " +
        "(case when \"Pivot Deaths\"=0 then \"Pivot Kills\" else \"Pivot Kills\" * 1.0 /\"Pivot Deaths\" end) as \"Pivot KD\", " +
        "(case when \"Untraded Deaths\"=0 then \"Untraded Kills\" else \"Untraded Kills\" * 1.0 /\"Untraded Deaths\" end) as \"Untraded KD\", " +
        "(case when Kills = 0 then 0 else (Kills - \"Untraded Kills\") * 1.0 /Kills end) as \"Traded Kill Ratio\", " +
        "(case when Deaths = 0 then 0 else (Deaths - \"Untraded Deaths\") * 1.0 /Deaths end) as \"Traded Death Ratio\" " +
        "from aggregated"
    )

    compiledStats = pd.concat([aggregated, combinedStats], axis=1)

    outputPath = str(Path(__file__).parent.parent) + "\\Output\\" + fileName + "_Stats.xlsx"
    writer = pd.ExcelWriter(outputPath)

    roundTable.to_excel(writer, sheet_name="Rounds", index=False)
    playerTable.to_excel(writer, sheet_name="Players", index=False)
    compiledStats.to_excel(writer, sheet_name="Overall", index=False)

    writer.close()