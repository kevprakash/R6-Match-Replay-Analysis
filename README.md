# R6-Match-Replay-Analysis

A parsing/analysis tool for use with Rainbow 6: Siege replay (.rec) files.

## Note on the Replay Parser
The majority of the ReplayParser module was not designed by me, but was translated from Go to Python by me. 
The original Go code (which will likely be more up-to-date and feature complete as just a parser) by [redraskal](https://github.com/redraskal) can be found [here](https://github.com/redraskal/r6-dissect). 
As the original parser is updated, this will also be updated.

A few notable optimizations and bug fixes in this version:
- Instead of reading directly from a decompression stream, this version of the parser decompresses the entire .rec file into a temporary file that is then read through. Not sure of the impact this has on performance, but it helps with debugging and reverse-engineering.
- Instead of scanning byte-by-byte, this version loads chunks of the decompressed file into a buffer then does a search for key byte sequences which it then directly jumps to. This makes the parser roughly 15x faster.
- There seems to be a bug in the original where the site validation byte is sometimes not found. This is because the validation byte changes depending on whether the recording player is on the attacking or defending side. This has been fixed in this version.
- Can find the recording player by using the profileID value (which works) instead of the ID value (which just doesn't work)

## Current Features
- Parse Replays (Refer to https://github.com/redraskal/r6-dissect for parsing features)
- Record team per-round data
    - Match ID
    - Round Number
    - Map
    - Defense Site
    - If the team was attack of defense
    - Whether attackers planted the defuser
    - Whether defenders disabled the defuser
    - If the team won or lost
    - What the win condition of the round was
- Record player per-round data
    - Player name
    - Match ID
    - Round Number
    - Operator
    - Spawn (**WIP**: Attacker spawns sometimes parsed incorrectly)
    - Kills
    - Headshots
    - Pivot Kills (An advanced metric)
    - Untraded Kills (An advanced metric)
    - If the player died
    - If the death was a pivot death (An advanced metric)
    - If the player got the opening kill
    - If the player was the opening death
    - If they completed an objective play (Plant/Disable)
    - If the player's death was traded (An advanced metric)
- Compile player stats for the whole match (or multiple matches)
    - Player name
    - Kills
    - Deaths
    - Headshot Kill Percentage
    - Pivot Kills (An advanced metric)
    - Pivot Deaths (An advanced metric)
    - Opening Kills
    - Opening Deaths
    - Untraded Kills (An advanced metric)
    - Untraded Deaths (An advanced metric)
    - KOST (An advanced metric)
    - KD
    - Pivot KD (An advanced metric)
    - Untraded KD (An advanced metric)
    - Traded Kill Ratio (An advanced metric)
    - Traded Death Ratio (An advanced metric)

## Advanced Metrics
**Pivot Kills, Deaths, KD**: This basically serves as a heuristic for what players would refer to as an "impact kill." The idea is that these kills in particular have an impact on the outcome of the round.
The way these are calculated are that a kill/death counts as an impact kill if: 
- Before the kill/death, the player count on both teams were the same
- All kills that bring a team back from a lower player count to an equal player count.
    - Example if a team is down 3 players, but one player gets 2 kills and the other gets 1 kill with neither dying, all 3 of those kills are pivot kills

Example of things that do not count as pivot kills/deaths:
- Getting 3 kills in a 1v5 then dying
- Getting 2 kills in a 4v2
- Dying in a 2v4

**Traded Kills, Deaths, KD**: Any kill/death in which the killer is killed within a certain time frame (default is 8 seconds). Untraded kills/deaths are any other kill/death.

**Traded Kill/Death Ratio**: The number of traded kills/deaths divided by the total number of kills/deaths. A lower Traded Kill Ratio is good, a higher Traded Death Ratio is good.

**KOST**: A metric that stands for **K**ill, **O**bjective, **S**urvived, **T**raded. Basically the ratio of rounds where a player did at least one of those things:
- They got a kill
- They made an objective player (planted/disabled defuser)
- The survived the round
- Their death was traded

## Usage
The simplest way to use this code for yourself is to edit R6MatchAnalysis.py as the comments on it suggest, then run it. It will output a .xlsx file to the Output folder.
You can use this as your stats reference for the match. You can also pass a folder of match replays (as the comments will guide you on) to process multiple matches. A (competitive) match takes roughly 2 minutes to process.

If you want to log multiple matches over a stretch of time, I suggest creating a different spreadsheet with the same columns as the Rounds and Players sheets,
then appending the rows from the output spreadsheet's respective sheets to that spreadsheet. You can then treat them like relational database tables 
(with the primary key of Rounds being Match ID, Round; and the primary key of Players being Name, Match ID, Round) and query them for any analytics you wish to do on your own.
If you wish to get the same compiled stats table that the Overall sheet provides, you can call compileStats() from Analyzer.py on your spreadsheet, which will add a sheet for Overall stats.
compileStats() has an optional parameter for if you want to process the overall stats on a per-match basis or on a totality basis. 

If you wish to just use the parser, just create a Reader object (from Reader.py) and pass it in the path to the .rec file you want to parse, then call .read() on the object. 
Afterwards the Reader object will contain the raw information from the match in its instance variables (the important ones are self.header and self.matchFeedback). 
Each Reader object can parse exactly one round (or one .rec file), so if you want to parse an entire match, iterate over the .rec files and create a Reader object for each one. 

