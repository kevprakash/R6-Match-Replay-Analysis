import zstandard
import ReplayParser.IDDecoding as IDDecoding
from ReplayParser.DataClasses import *
import io
import time
from pathlib import Path
import ntpath, os

# Literals
strSeparator = b'\x00\x00\x00\x00\x00\x00\x00'


class Reader:
    def __init__(self, filePath, relative=False):
        super().__init__()
        # Vars
        self.filePath = filePath
        self.fileName = filePath
        self.decompressFilePath = None
        self.dStream = None
        self.rawStream = None
        self.getDecompressionStream(self.filePath, relative=relative)
        self.queries = []
        self.listeners = []
        self.time = -1
        self.timeRaw = ""
        self.lastDefuserPlayerIndex = -1
        self.disableStartTimer = -1
        self.planted = False
        self.numBytesRead = 0
        self.matchFeedback = []
        self.roundEnded = False

        self.buffer = bytearray()

        self.header = None

        self.playersRead = 0

        self.listen(bytearray(b'\x40' + b'\xF2' + b'\x15' + b'\x04'), self.readPlayer)
        self.listen(bytearray(b'\x22' + b'\xa9' + b'\x26' + b'\x0B' + b'\xe4'), self.readAtkOpSwap)
        self.listen(bytearray(b'\xaf' + b'\x98' + b'\x99' + b'\xca'), self.readSpawn)
        self.listen(bytearray(b'\x1f' + b'\x07' + b'\xef' + b'\xc9'), self.readTime)
        self.listen(bytearray(b'\x59' + b'\x34' + b'\xe5' + b'\x8b' + b'\x04'), self.readMatchFeedback)
        self.listen(bytearray(b'\x22' + b'\xa9' + b'\xc8' + b'\x58' + b'\xd9'), self.readDefuserTimer)

    def decompressFile(self, fileName, verbose=False):
        outputPath = str(Path(__file__).parent.parent) + "\\temp\\" + fileName + ".decompressed"
        if verbose:
            print("Decompressing", self.filePath, "to", outputPath)
        writeStream = open(outputPath, 'wb+')
        chunkSize = 8192
        while True:
            try:
                chunk = self.readWrapper(chunkSize, readSize=chunkSize, verbose=False)
                writeStream.write(chunk)
            except zstandard.ZstdError:
                writeStream.close()
                self.dStream.close()
                break

        self.rawStream = io.open(outputPath, 'rb')
        self.dStream = io.BufferedReader(self.rawStream, buffer_size=1024 ** 3)
        self.decompressFilePath = outputPath

    def playerIndexByID(self, id):
        for i in range(len(self.header.players)):
            p = self.header.players[i]
            if id == p.id:
                return i
        return -1

    def playerIndexByUsername(self, username):
        for i in range(len(self.header.players)):
            p = self.header.players[i]
            if username == p.username:
                return i
        raise Exception("No player with name: " + username)

    def getDecompressionStream(self, filePath, relative):
        if relative:
            filePath = str(Path(__file__).parent.parent) + "\\" + filePath
            self.filePath = filePath
        else:
            self.fileName = ntpath.basename(filePath)
        replayFile = open(self.filePath, 'rb')
        self.rawStream = replayFile
        self.dStream = zstandard.ZstdDecompressor().stream_reader(replayFile,  read_size=1024 ** 3, read_across_frames=True)

    def readBytes(self, length):
        return self.dStream.read(length)

    def readWrapper(self, length, readSize=64 * (1024 ** 2), verbose=True):
        while len(self.buffer) < length:
            try:
                readBytes = bytearray(self.dStream.read(readSize))
                self.buffer.extend(readBytes)
                self.numBytesRead += readSize
                if verbose:
                    print("Total bytes read:", self.numBytesRead)

            # If you've reached the end of the readable part of the file,
            # cut the read size in half to make sure you don't miss anything
            except zstandard.ZstdError as e:
                readSize = readSize // 2
                # If the read size is 0, there's literally nothing left to read
                if readSize == 0:
                    raise zstandard.ZstdError

        b = bytes(self.buffer[:length])
        del self.buffer[:length]

        return b

    def byteToInt(self, b, signed=True, hex=False, verbose=False, little=False):
        if hex:
            i = int.from_bytes(b, "little" if little else "big", signed=signed)
        else:
            i = int(b.decode())

        if verbose:
            print(b, "->", i)
        return i

    def readInt(self):
        b = self.readBytes(1)
        return self.byteToInt(b, hex=True)

    def readUint64(self, verbose=False):
        self.readBytes(1)
        b = self.readBytes(8)
        if verbose:
            print(b.hex())
        l = self.byteToInt(b, signed=False, hex=True, verbose=False, little=True)

        return l

    def readUint32(self, verbose=False):
        self.readBytes(1)
        b = self.readBytes(4)
        if verbose:
            print(b.hex())
        l = self.byteToInt(b, signed=False, hex=True, verbose=False, little=True)

        return l

    def readString(self):
        size = self.readInt()
        b = self.readBytes(size)
        return b.decode()

    def listen(self, b, listener):
        self.queries.append(b)
        self.listeners.append(listener)

    def getRecordingPlayerSide(self, verbose=False):
        # This derives the team roles in case all 10 players aren't processed yet
        self.deriveTeamRoles(verbose=verbose)
        for p in self.header.players:
            if p.profileID == self.header.recordingProfileID:
                return self.header.teams[p.teamIndex].role
        return "Attack"                                         # As far as I can tell the attackers are processed after defenders

    # Reads magic bytes and validates
    def readHeaderMagic(self, verbose=True):
        if verbose:
            print("Started reading Magic Bytes")
        # The first seven bytes in the file should say "dissect"
        mhBytes = self.readBytes(7)
        if mhBytes != b'dissect':
            raise Exception("Invalid Magic Bytes:", mhBytes)

        # There should be 2 sequences of 7 \x00 bytes
        # We are trying to skip to the end of the second one
        n = 0
        t = 0
        while t < 2:
            mhByte = self.readBytes(1)
            if mhByte == b'\x00':
                if n < 6:
                    n += 1
                else:
                    n = 0
                    t += 1
            else:
                n = 0

        if verbose:
            print("Finished reading Magic Bytes")

    # Reads the header of the data
    # Game Settings, players, rounds, etc
    def readHeader(self, verbose=True):
        if verbose:
            print("Started Reading Header")
        props = {}
        gmSettings = []
        players = []
        currentPlayer = Player()
        playerData = False
        lastProp = False

        while not lastProp:
            k = self.readHeaderString().decode()
            v = self.readHeaderString()

            if k == "playerid":
                if playerData:
                    players.append(currentPlayer)
                playerData = True
                currentPlayer = Player()

            if (k == "playlistcategory" or k == "id") and playerData:
                players.append(currentPlayer)
                playerData = False

            if not playerData:
                if k != "gmsetting":
                    props[k] = v
                else:
                    n = self.byteToInt(v)
                    gmSettings.append(n)
            else:
                match k:
                    case "playerid":
                        n = self.byteToInt(v)
                        currentPlayer.ID = n
                    case "playername":
                        currentPlayer.username = v.decode()
                    case "team":
                        n = self.byteToInt(v)
                        currentPlayer.teamIndex = n
                    case "heroname":
                        n = self.byteToInt(v)
                        currentPlayer.HeroName = n
                    case "alliance":
                        n = self.byteToInt(v)
                        currentPlayer.alliance = n
                    case "roleimage":
                        n = self.byteToInt(v)
                        currentPlayer.roleImage = n
                    case "rolename":
                        currentPlayer.roleName = v.decode()
                    case "roleportrait":
                        n = self.byteToInt(v)
                        currentPlayer.rolePortrait = n

            lastProp = "teamscore1" in props.keys()

        h = Header(teams=[Team(), Team()], players=players, gmSettings=gmSettings)

        # Parse properties
        h.gameVer = props["version"].decode()
        h.codeVer = self.byteToInt(props["code"])
        h.timestamp = props["datetime"].decode() # Probably update this later to actually parse the datetime
        h.matchType = self.byteToInt(props["matchtype"])
        h.map = self.byteToInt(props["worldid"])
        h.recordingPlayerID = self.byteToInt(props["recordingplayerid"])
        h.recordingProfileID = props["recordingprofileid"].decode()
        h.additionalTags = props["additionaltags"].decode()
        h.gameMode = self.byteToInt(props["gamemodeid"])
        h.roundsPerMatch = self.byteToInt(props["roundspermatch"])
        h.roundsPerMatchOT = self.byteToInt(props["roundspermatchovertime"])
        h.roundNumber = self.byteToInt(props["roundnumber"])
        h.OTRoundNumber = self.byteToInt(props["overtimeroundnumber"])
        h.teams[0].name = props["teamname0"].decode()
        h.teams[1].name = props["teamname1"].decode()
        h.matchID = props["id"].decode()
        h.teams[0].score = self.byteToInt(props["teamscore0"])
        h.teams[1].score = self.byteToInt(props["teamscore1"])

        # Playlist category needs a bit of special processing
        if ("playlistcategory" in props.keys()) and len(props["playlistcategory"]) > 0:
            try:
                n = self.byteToInt(props["playlistcategory"])
            except Exception:
                pass
            else:
                h.playlistCategory = n

        if verbose:
            print("Finished reading Header")
        return h

    # For use while parsing the header
    def readHeaderString(self):
        strLen = self.readBytes(1)       # Read the length of the string
        sepBytes = self.readBytes(7)     # Read the string separator

        if sepBytes != strSeparator:
            raise Exception("Invalid String Separator: " + str(sepBytes))

        strBytes = self.readBytes(self.byteToInt(strLen, hex=True))

        return strBytes

    # Seek until we reach a specific byte pattern
    def seek(self, query):
        i = 0
        while True:
            b = self.readBytes(1)
            if b != query[i]:
                i = 0
                continue

            i += 1

            if i == len(query):
                return

    def seekToQuery(self, scanSize=1024 ** 2):
        subBuffer = self.dStream.peek(scanSize)
        nearestIndex = -1
        maxQLen = 0
        for q in self.queries:
            inBuffer = q in subBuffer
            if inBuffer:
                index = subBuffer.index(bytes(q))
                nearestIndex = min(index, nearestIndex) if nearestIndex > -1 else index
                maxQLen = max(maxQLen, len(q))
        if nearestIndex < 0:
            readAmount = max(1, len(subBuffer) - maxQLen)
            x = self.dStream.read(readAmount)
            self.numBytesRead += readAmount
            return False, x == b''
        else:
            self.dStream.read(nearestIndex)
            self.numBytesRead += nearestIndex
            return True, False

    def read(self, verbose=True):
        startTime = time.time()

        self.decompressFile(self.fileName, verbose=verbose)

        self.readHeaderMagic(verbose)
        self.header = self.readHeader(verbose)

        self.numBytesRead = 0

        indices = [0 for _ in range(len(self.queries))]

        if verbose:
            print("Started Listening for events")

        foundQuery = False
        eof = False

        while True:
            # Read the next byte and pray there isn't  an error
            try:
                while not foundQuery:
                    foundQuery, eof = self.seekToQuery()
                    if self.roundEnded or eof:
                        break
                dataByte = self.readBytes(1)
            except Exception as e:
                print(type(e).__name__)
                break

            if self.roundEnded or eof:
                break

            partialMatch = False
            for i in range(len(self.queries)):
                query = self.queries[i]
                index = indices[i]
                queryByte = bytes(query[index:index+1])
                if dataByte == queryByte:
                    partialMatch = True
                    indices[i] += 1
                    # If they query pattern is fully matched, run the appropriate listener
                    if indices[i] == len(query):
                        indices[i] = 0
                        self.listeners[i](verbose=verbose)
                        '''
                        try:
                            self.listeners[i](verbose=verbose)
                        except Exception:
                            traceback.print_stack()
                            return
                        '''
                else:
                    indices[i] = 0

            if not partialMatch:
                foundQuery = False

        self.dStream.close()
        self.rawStream.close()
        os.remove(self.decompressFilePath)

        endTime = time.time()
        if verbose:
            print("File processing took", format(endTime - startTime, "03.1f"), "seconds")

    # ---------------------- LISTENER FUNCTIONS ---------------------------------------
    def readPlayer(self, verbose=True):

        idIndicator = [b'\x33', b'\xd8', b'\x3d', b'\x4f', b'\x23']
        spawnIndicator = [b'\xaf', b'\x98', b'\x99', b'\xca']
        usernameIndicator = [b'\x22', b'\x85', b'\xcf', b'\x36', b'\x3a']
        profileIDIndicator = [b'\x8a', b'\x50', b'\x9b', b'\xd0']

        self.playersRead += 1

        self.readBytes(8)               # Skip the next 8 bytes
        swap = self.readBytes(1)

        if swap == b'\x9d':
            return None

        op = self.readUint64()

        if op == 0:
            return None

        self.seek(idIndicator)
        id = self.byteToInt(self.readBytes(4), hex=True, signed=False)

        self.seek(spawnIndicator)
        spawn = self.readString()
        if (spawn is None) or (spawn == ""):
            self.readBytes(10)
            valid = self.readBytes(1)
            if valid != b'\x1b':
                return None

        self.seek(usernameIndicator)
        teamIndex = 0 if self.playersRead <= 5 else 1
        username = self.readString()

        profileID = ""
        unknownID = -1
        if self.header.recordingPlayerID > 0:
            self.seek(profileIDIndicator)
            profileID = self.readString()

            _ = self.readBytes(5)                   # Skipping these values but it should be 22eed445c8
            unknownID = self.readUint64()

        else:
            # Player IDs aren't recorded in this replay
            pass

        p = Player(
            ID=unknownID,
            profileID=profileID,
            username=username,
            teamIndex=teamIndex,
            operator=op,
            spawn=spawn,
            id=id
        )

        found = False

        for i in range(len(self.header.players)):
            existing = self.header.players[i]
            if (existing.username == p.username) or (existing.id == p.id):
                self.header.players[i].ID = p.ID
                self.header.players[i].profileID = p.profileID
                self.header.players[i].username = p.username
                self.header.players[i].teamIndex = p.teamIndex
                self.header.players[i].operator = p.operator
                self.header.players[i].spawn = p.spawn
                self.header.players[i].id = p.id
                found = True

                break

        if (not found) and (len(username) > 0):
            self.header.players.append(p)

        if self.playersRead == 10:
            self.deriveTeamRoles(verbose=verbose)
        if verbose:
            print("Read Player:", p.username)

    def deriveTeamRoles(self, verbose=True):
        for p in self.header.players:
            try:
                role = IDDecoding.getOpRoleByID(p.operator)
            except KeyError as e:
                if verbose:
                    print("Could not find operator with ID:", p.operator)
                    if p.roleName is not None:
                        print("Could possibly be:", p.roleName)

                if p.roleName is not None:
                    role = IDDecoding.getOpRoleByName(p.roleName.lower())
                else:
                    continue
            teamIndex = p.teamIndex
            oppTeamIndex = teamIndex ^ 1
            pass
            self.header.teams[teamIndex].role = role
            self.header.teams[oppTeamIndex].role = "Defense" if (role == "Attack") else "Attack"

    def readAtkOpSwap(self, verbose=True):
        op = self.readUint64()
        self.readBytes(5)       # Skip the next 5 bytes
        id = self.byteToInt(self.readBytes(4), hex=True, signed=False)
        try:
            i = self.playerIndexByID(id)
        except Exception:
            return
        if i > -1:
            self.header.players[i].operator = op
            u = MatchUpdate(type=MatchUpdateType.OperatorSwap, username=self.header.players[i].username, time=self.timeRaw, timeInSeconds=self.time, operator=op)
            self.matchFeedback.append(u)
            if verbose:
                print(self.header.players[i].username, "swapped operators at", self.timeRaw)

    def readSpawn(self, verbose=True):
        location = self.readString()
        self.readBytes(6)               # Skip the next 6 bytes
        site = self.readBytes(1)

        recordingSide = self.getRecordingPlayerSide(verbose)
        pass

        siteFlag = None

        if recordingSide == "Attack":
            siteFlag = b'\x02'
        elif recordingSide == "Defense":
            siteFlag = b'\x03'

        if site == siteFlag:
            formatted = location.replace("<br/>", ", ", 1)
            for i in range(len(self.header.players)):
                p = self.header.players[i]
                if self.header.teams[p.teamIndex].role == "Defense":
                    p.spawn = formatted
            self.header.site = formatted
            if verbose:
                print("Read Spawn:", formatted)

    def readTime(self, verbose=True):
        time = self.readUint32()
        if self.time == 0:
            if (time == 11) or self.planted:
                self.roundEnd(verbose=verbose)

        self.time = float(time)
        self.timeRaw = str(int(self.time//60)) + ":" + format(self.time % 60, "04.1f")
        if verbose:
            print("Time:", self.timeRaw)

    def roundEnd(self, verbose=True):
        if verbose:
            print("Round End")
        self.roundEnded = True
        planter = -1
        deaths = [0, 0]
        sizes = [0, 0]
        roles = [None, None]

        for p in self.header.players:
            sizes[p.teamIndex] = sizes[p.teamIndex] + 1
            roles[p.teamIndex] = self.header.teams[p.teamIndex].role

        for u in self.matchFeedback:
            if u.type == MatchUpdateType.Kill:
                i = self.header.players[self.playerIndexByUsername(u.target)].teamIndex
                deaths[i] = deaths[i] + 1
            if u.type == MatchUpdateType.Death:
                i = self.header.players[self.playerIndexByUsername(u.username)].teamIndex
                deaths[i] = deaths[i] + 1
            if u.type == MatchUpdateType.DefuserPlantComplete:
                planter = self.playerIndexByUsername(u.username)
            if u.type == MatchUpdateType.DefuserDisableComplete:
                i = self.header.players[self.playerIndexByUsername(u.username)].teamIndex
                self.header.teams[i].won = True
                self.header.teams[i].winCondition = "Disabled Defuser"
                return

        if planter > -1:
            i = self.header.players[planter].teamIndex
            self.header.teams[i].won = True
            self.header.teams[i].winCondition = "Defused Bomb"
            return

        if deaths[0] == sizes[0]:
            if (planter > -1) and (roles[0] == "Attack"):
                return
            self.header.teams[1].won = True
            self.header.teams[1].winCondition = "Killed Opponents"
            return

        if deaths[1] == sizes[1]:
            if (planter > -1) and (roles[1] == "Attack"):
                return
            self.header.teams[0].won = True
            self.header.teams[0].winCondition = "Killed Opponents"
            return

        i = 0
        if roles[1] == "Defense":
            i = 1

        self.header.teams[i].won = True
        self.header.teams[i].winCondition = "Time"

    def readMatchFeedback(self, verbose=True):
        activity = [b'\x00', b'\x00', b'\x00', b'\x22', b'\xe3', b'\x09', b'\x00', b'\x79']
        killIndicator = b'\x22\xd9\x13\x3c\xba'

        bombIndicator = self.readBytes(1)                   # Not used but might be useful in the future
        self.seek(activity)
        size = self.readInt()
        if size == 0:
            killTrace = self.readBytes(5)
            if killTrace != killIndicator:
                return None
            username = self.readString()
            empty = len(username) == 0
            if empty and verbose:
                print("Username empty for feedback event")

            self.readBytes(15)                              # Skip the next 15 bytes. Might contain info though?

            target = self.readString()
            if empty and (len(target) > 0):
                u = MatchUpdate(
                    type=MatchUpdateType.Death,
                    username=target,
                    time=self.timeRaw,
                    timeInSeconds=self.time
                )
                self.matchFeedback.append(u)
                if verbose:
                    print("Death of", username, "at", self.timeRaw)
                return None
            elif empty:
                return

            u = MatchUpdate(
                type=MatchUpdateType.Kill,
                username=username,
                target=target,
                time=self.timeRaw,
                timeInSeconds=self.time
            )
            self.readBytes(56)                  # Skip 56 bytes, maybe parse through for potentially useful information
            headshot = self.readInt()
            u.headshot = headshot == 1

            # Filter out duplicate events
            for val in self.matchFeedback:
                if (val.type == MatchUpdateType.Kill) and (val.username == u.username) and (val.target == u.target):
                    return None

            self.matchFeedback.append(u)
            if verbose:
                print(u.username, "killed", u.target, "at", self.timeRaw, "" if headshot != 1 else "with a headshot")
            return None

        b = self.readBytes(size)
        msg = b.decode()
        t = MatchUpdateType.Other
        if ("bombs" in msg) or ("objective" in msg):
            t = MatchUpdateType.LocatedObjective
        if "left" in msg:
            t = MatchUpdateType.PlayerLeave
        if "BattlEye" in msg:
            t = MatchUpdateType.Battleye
        uName = msg.split(" ")[0]
        if t == MatchUpdateType.Other:
            uName = ""
        else:
            msg = ""
        u = MatchUpdate(
            type=t,
            username=uName,
            target="",
            time=self.timeRaw,
            timeInSeconds=self.time,
            message=msg
        )
        self.matchFeedback.append(u)
        if verbose:
            print("Match Update:", u)
        return None

    def readDefuserTimer(self, verbose=True):
        timer = self.readString()
        self.readBytes(34)
        id = self.byteToInt(self.readBytes(4), hex=True, signed=False)
        try:
            i = self.playerIndexByID(id)
        except Exception:
            return
        a = MatchUpdateType.DefuserPlantStart if not self.planted else MatchUpdateType.DefuserDisableStart

        if i > -1:
            u = MatchUpdate(
                type=a,
                username=self.header.players[i].username,
                time=self.timeRaw,
                timeInSeconds=self.time
            )
            self.matchFeedback.append(u)
            if verbose:
                print(self.header.players[i].username, "started", "planting" if not self.planted else "disabling", "at", self.timeRaw)
            self.lastDefuserPlayerIndex = i
            if self.planted:
                self.disableStartTimer = self.time

        if not timer.startswith("0.00"):
            # This should account for when the timer hits 0
            # but the defuser is not disabled in time
            if self.planted and (self.disableStartTimer > 7):
                return None
            if not self.planted:
                return None

        a = MatchUpdateType.DefuserPlantComplete if not self.planted else MatchUpdateType.DefuserDisableComplete

        if verbose:
            print(self.header.players[self.lastDefuserPlayerIndex].username, "finished", "planting" if not self.planted else "disabling", "at", self.timeRaw)

        if not self.planted:
            self.planted = True

        u = MatchUpdate(
            type=a,
            username=self.header.players[self.lastDefuserPlayerIndex].username,
            time=self.timeRaw,
            timeInSeconds=self.time
        )

        self.matchFeedback.append(u)
        return None