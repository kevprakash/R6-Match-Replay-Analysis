MapIDNamePairs = [
    ("ClubHouse", 837214085),  ("KafeDostoyevsky", 1378191338),
    ("Kanal", 1460220617),  ("Yacht", 1767965020),  ("PresidentialPlane", 2609218856),
    ("ConsulateY7", 2609221242),  ("BartlettU", 2697268122),  ("Coastline", 42090092951),
    ("Tower", 53627213396),  ("Villa", 88107330328),  ("Fortress", 126196841359),  ("HerefordBase", 127951053400),
    ("ThemePark", 199824623654),  ("Oregon", 231702797556),  ("House", 237873412352),  ("Chalet", 259816839773),
    ("Skyscraper", 276279025182),  ("Border", 305979357167),  ("Favela", 329867321446),  ("Bank", 355496559878),
    ("Outback", 362605108559),  ("EmeraldPlains", 365284490964),  ("StadiumBravo", 270063334510),
    ("NighthavenLabs", 378595635123),  ("Consulate", 379218689149),
]

MapIDDecoder = {x[1]: x[0] for x in MapIDNamePairs}
MapNameEncoder = {x[0]: x[1] for x in MapIDNamePairs}

OperatorIDNamePairs = [
    ("Castle", 92270642682), ("Aruni", 104189664704), ("Kaid", 161289666230), ("Mozzie", 174977508820), 
    ("Pulse", 92270642708), ("Ace", 104189664390), ("Echo", 92270642214), ("Azami", 378305069945), 
    ("Solis", 391752120891), ("Capitao", 92270644215), ("Zofia", 92270644189), ("Dokkaebi", 92270644267), 
    ("Warden", 104189662920), ("Mira", 92270644319), ("Sledge", 92270642344), ("Melusi", 104189664273), 
    ("Bandit", 92270642526), ("Valkyrie", 92270642188), ("Rook", 92270644059), ("Kapkan", 92270641980), 
    ("Zero", 291191151607), ("Iana", 104189664038), ("Ash", 92270642656), ("Blackbeard", 92270642136), 
    ("Osa", 288200867444), ("Thorn", 373711624351), ("Jäger", 92270642604), ("Kali", 104189663920),
    ("Thermite", 92270642760), ("Brava", 288200866821), ("Amaru", 104189663607), ("Ying", 92270642292), 
    ("Lesion", 92270642266), ("Doc", 92270644007), ("Lion", 104189661861), ("Fuze", 92270642032), 
    ("Smoke", 92270642396), ("Vigil", 92270644293), ("Mute", 92270642318), ("Goyo", 104189663698), 
    ("Wamai", 104189663803), ("Ela", 92270644163), ("Montagne", 92270644033), ("Nokk", 104189663024), 
    ("Alibi", 104189662071), ("Finka", 104189661965), ("Caveira", 92270644241), ("Nomad", 161289666248), 
    ("Thunderbird", 288200867351), ("Sens", 384797789346), ("IQ", 92270642578), ("Blitz", 92270642539), 
    ("Hibana", 92270642240), ("Maverick", 104189662384), ("Flores", 328397386974), ("Buck", 92270642474), 
    ("Twitch", 92270644111), ("Gridlock", 174977508808), ("Thatcher", 92270642422), ("Glaz", 92270642084), 
    ("Jackal", 92270644345), ("Grim", 374667788042), ("Tachanka", 291437347686), ("Oryx", 104189664155), 
    ("Frost", 92270642500), ("Maestro", 104189662175), ("Clash", 104189662280), ("Fenrir", 288200867339),
]

OperatorIDDecoder = {x[1]: x[0].lower() for x in OperatorIDNamePairs}
OperatorNameEncoder = {x[0].lower(): x[1] for x in OperatorIDNamePairs}

OperatorRoles = [
    ("Castle", "Defense"), ("Aruni", "Defense"), ("Kaid", "Defense"), ("Mozzie", "Defense"),
    ("Pulse", "Defense"), ("Ace", "Defense"), ("Echo", "Defense"), ("Azami", "Defense"),
    ("Solis", "Defense"), ("Capitao", "Attack"), ("Zofia", "Attack"), ("Dokkaebi", "Attack"),
    ("Warden", "Defense"), ("Mira", "Defense"), ("Sledge", "Attack"), ("Melusi", "Defense"),
    ("Bandit", "Defense"), ("Valkyrie", "Defense"), ("Rook", "Defense"), ("Kapkan", "Defense"),
    ("Zero", "Attack"), ("Iana", "Attack"), ("Ash", "Attack"), ("Blackbeard", "Attack"),
    ("Osa", "Attack"), ("Thorn", "Defense"), ("Jäger", "Defense"), ("Kali", "Attack"),
    ("Thermite", "Attack"), ("Brava", "Attack"), ("Amaru", "Attack"), ("Ying", "Attack"),
    ("Lesion", "Defense"), ("Doc", "Defense"), ("Lion", "Attack"), ("Fuze", "Attack"),
    ("Smoke", "Defense"), ("Vigil", "Defense"), ("Mute", "Defense"), ("Goyo", "Defense"),
    ("Wamai", "Defense"), ("Ela", "Defense"), ("Montagne", "Attack"), ("Nokk", "Attack"),
    ("Alibi", "Defense"), ("Finka", "Attack"), ("Caveira", "Defense"), ("Nomad", "Attack"),
    ("Thunderbird", "Defense"), ("Sens", "Attack"), ("IQ", "Attack"), ("Blitz", "Attack"),
    ("Hibana", "Attack"), ("Maverick", "Attack"), ("Flores", "Attack"), ("Buck", "Attack"),
    ("Twitch", "Attack"), ("Gridlock", "Attack"), ("Thatcher", "Attack"), ("Glaz", "Attack"),
    ("Jackal", "Attack"), ("Grim", "Attack"), ("Tachanka", "Defense"), ("Oryx", "Defense"),
    ("Frost", "Defense"), ("Maestro", "Defense"), ("Clash", "Defense"), ("Fenrir", "Defense"),
]

OperatorRolesDict = {x[0].lower():x[1] for x in OperatorRoles}


def getMapName(mapID):
    try:
        return MapIDDecoder[mapID]
    except KeyError:
        return "Unknown"


def getOpName(opID):
    try:
        return OperatorIDDecoder[opID]
    except KeyError:
        return "Unknown"


def getOpRoleByName(opName):
    return OperatorRolesDict[opName]


def getOpRoleByID(opID):
    return getOpRoleByName(getOpName(opID))