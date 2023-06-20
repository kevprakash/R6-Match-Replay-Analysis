import ReplayAnalyzer.Analyzer as Analyzer
from ReplayParser.Reader import Reader

# Replace this with the players you want to track (ALL MUST BE ON THE SAME TEAM)
# Keys are the name you want to refer to them by
# Values are list of in-game names used by them
players = {
    "Arc": ["Arcturus.-"],
    "Godly": ["Mightster.-"],
    "Derpy": ["Derpydoge2023.-", "Derpydoge2023"],
    "Asylum": ["Asylum.--"],
    "Chromeo": ["Chromeo.-"]
}

# Replace this with where your replay is stored (typically in the Siege installation folder under MatchReplays)
MatchDirectory = "C:\\Users\\kevpr\\Desktop\\2023 Dallas LAN Replays\\Unorganized\\"

# These are just to specify which rec file to use
MatchName = "Match-2023-06-02_09-05-40-168\\"
RoundName = "Match-2023-06-02_09-05-40-168-R08.rec"
filePath = MatchDirectory + MatchName + RoundName

r = Reader(filePath)
r.read(verbose=True, deleteDecompressed=False)      # This will decompress the file and keep it
pass                                                # Add a breakpoint here so you can read the values in r
