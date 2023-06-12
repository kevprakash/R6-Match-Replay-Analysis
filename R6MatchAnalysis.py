import ReplayAnalyzer.Analyzer as Analyzer

# Replace this with the players you want to track (ALL MUST BE ON THE SAME TEAM)
players = ["Arcturus.-", "Mightster.-", "Derpydoge2023.-", "Asylum.--", "Chromeo.-"]
# Replace this with where your replay is stored (typically in the Siege installation folder under MatchReplays)
MatchDirectory = "C:\\Users\\kevpr\\Desktop\\2023 Dallas LAN Replays\\"
# Replace this with the folder name of the match (no trailing or leading slashes"
MatchName = "Match-2023-06-03_08-28-11-247"
# You can leave these as is
Analyzer.processMatch(MatchDirectory + MatchName, players, parserVerbose=False)
Analyzer.compileStats(MatchName)