import ReplayAnalyzer.Analyzer as Analyzer

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

# You can leave these as is, just uncomment which ones you want to use

'''
# Single Match------------------------------------------------------------------------------------------

# Replace this with the folder name of the match (no trailing or leading slashes"
MatchName = "Match-2023-06-03_08-28-11-247"
Analyzer.processMatch(MatchDirectory + MatchName, players, parserVerbose=False)
Analyzer.compileStats(MatchName)
'''

# Multiple Matches--------------------------------------------------------------------------------------

# Replace this with whatever you want to call the save file
saveName = "DALLAS_LAN"
Analyzer.processMultipleMatches(MatchDirectory, "Dallas_LAN", players, parserVerbose=False)
Analyzer.compileStats(saveName)