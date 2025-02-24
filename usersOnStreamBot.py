from string_query import string_query
import json
import re
from datetime import datetime
import pytz
import tzlocal
import time
import sqlite3
import requests
import os

if os.path.isfile('localconfig.json'):
  with open('localconfig.json', 'r') as file:
    config = json.load(file)
else:
  with open('config.json', 'r') as file:
    config = json.load(file)
print(config)
numSavedSets = config["numSavedSets"]
recencyIntervalDays = config["recencyIntervalDays"]
startggToken = config["startggToken"]
discordBotToken = config["discordBotToken"]
discordChannelId = config["discordChannelId"]
roleMention = config["roleMention"]
subtextStr = config["subtextStr"]
startggHeaders = {"Authorization": f"Bearer {startggToken}"}
discordHeaders = {
  "Authorization": f"Bot {discordBotToken}",
  "Content-Type": "application/json"
}
setsPerPage = 40
apiInterval = 0.8

con = sqlite3.connect("current_sets.db")
cur = con.cursor()
try:
  cur.executescript("CREATE TABLE tourneyset(timefound, setid)")
except:
  print("")
try:
  cur.executescript(f"""
   CREATE TRIGGER n_rows_only AFTER INSERT ON tourneyset
   BEGIN
     DELETE FROM tourneyset WHERE timefound <= (SELECT timefound FROM tourneyset ORDER BY timefound DESC LIMIT {numSavedSets}, 1);
   END;
""")
except:
  print("")

api_timestamp = 0
while True:
  if os.path.isfile('localUserSlugs.json'):
    with open('localUserSlugs.json', 'r') as file:
      userSlugs = json.load(file)
  else:
    with open('userSlugs.json', 'r') as file:
      userSlugs = json.load(file)
  print(userSlugs)
  querystrings = []
  querystrings.append("query Users {")
  #TODO: batch sets queries while staying under start.gg object limit
  #slugs = [slug for slug in userSlugs.values()[:5]]
  names = []
  count = 0
  for key in userSlugs:
    names.append(key)
  for name in names:
    slug = userSlugs[name]
    querystrings.append(f'  slug{slug}:user(slug:"{slug}") {{')
    querystrings.append("    id")
    querystrings.append("    discriminator")
    querystrings.append("    player{")
    querystrings.append("      id")
    querystrings.append("      gamerTag")
    querystrings.append(f"      sets(perPage: {setsPerPage}, page: 1, filters:{{state: [2]}}) {{")
    querystrings.append("        pageInfo {")
    querystrings.append("          total")
    querystrings.append("          filter")
    querystrings.append("          totalPages")
    querystrings.append("        }")
    querystrings.append("        nodes {")
    querystrings.append("          id")
    querystrings.append("          completedAt")
    querystrings.append("          identifier")
    querystrings.append("          startAt")
    querystrings.append("          state")
    querystrings.append("          stream {")
    querystrings.append("            id")
    querystrings.append("            enabled")
    querystrings.append("            isOnline")
    querystrings.append("            parentStreamId")
    querystrings.append("            streamId")
    querystrings.append("            streamLogo")
    querystrings.append("            streamName")
    querystrings.append("            streamType")
    querystrings.append("            streamSource")
    querystrings.append("            streamType")
    querystrings.append("            streamTypeId")
    querystrings.append("            streamStatus")
    querystrings.append("            numSetups")
    querystrings.append("          }")
    querystrings.append("          event {")
    querystrings.append("            name")
    querystrings.append("            slug")
    querystrings.append("            startAt")
    querystrings.append("          }")
    querystrings.append("          slots(includeByes: false) {")
    querystrings.append("            entrant {")
    querystrings.append("              id")
    querystrings.append("              name")
    querystrings.append("              participants {")
    querystrings.append("                player {")
    querystrings.append("                  id")
    querystrings.append("                  user {")
    querystrings.append("                    id")
    querystrings.append("                  }")
    querystrings.append("                }")
    querystrings.append("              }")
    querystrings.append("            }")
    querystrings.append("          }")
    querystrings.append("          games {")
    querystrings.append("            id")
    querystrings.append("            selections {")
    querystrings.append("              selectionType")
    querystrings.append("              selectionValue")
    querystrings.append("              entrant {")
    querystrings.append("                id")
    querystrings.append("                name")
    querystrings.append("                participants {")
    querystrings.append("                  player {")
    querystrings.append("                    gamerTag")
    querystrings.append("                    id")
    querystrings.append("                  }")
    querystrings.append("                }")
    querystrings.append("              }")
    querystrings.append("            }")
    querystrings.append("          }")
    querystrings.append("          vodUrl")
    querystrings.append("          winnerId")
    querystrings.append("          fullRoundText")
    querystrings.append("          wPlacement")
    querystrings.append("          lPlacement")
    querystrings.append("          displayScore")
    querystrings.append("        }")
    querystrings.append("      }")
    querystrings.append("    }")
    querystrings.append("  }")
  querystrings.append("}")
  querystring = "\n".join(querystrings)
  new_timestamp = time.time()
  time_diff = new_timestamp - api_timestamp
  api_timestamp = new_timestamp
  print("time_diff:", time_diff)
  if api_timestamp != 0 and time_diff < apiInterval:
    print("sleep:", apiInterval - time_diff)
    time.sleep(apiInterval - time_diff)

  data = string_query(querystring, {}, startggHeaders)
  if data is None or "data" not in data:
      print(data)
      continue
  after_timestamp = time.time()
  print("api_time:", after_timestamp - api_timestamp)

  users = list(data["data"].values())
  for user in users:
    print("User:", user)
    try:
      playerId = user["player"]["id"]
      userId = user["id"]
      gamerTag = user["player"]["gamerTag"]
    except:
      continue
    setNodes = None
    charValueCounts = {}
    eventIds = []

    if "player" not in user:
      continue
    player = user["player"]
    if "sets" not in player:
      continue
    sets = player["sets"]
    if sets is None:
      continue

    numPages = sets["pageInfo"]["totalPages"]
    setNodes = sets["nodes"]
    local_timezone = tzlocal.get_localzone()
    date_format = '%Y-%m-%d %I:%M %p (%Z)'
    recencyInterval = 60*60*24*recencyIntervalDays #filters out active sets that were never reported
    for setNode in setNodes:
      print(setNode)
      winnerId = setNode["winnerId"]
      fullRoundText = setNode["fullRoundText"]
      slots = setNode["slots"]
      event = setNode["event"]
      slot1 = slots[0]
      slot2 = slots[1]
      setid = setNode["id"]
      entrant1 = slot1["entrant"]
      entrant2 = slot2["entrant"]
      if entrant1 is None:
        continue
      if entrant2 is None:
        continue
      print(setNode)
      if winnerId == None:
        stream = setNode["stream"]
        streamName = None
        streamUrl = None
        if stream is not None:
          streamName = stream["streamName"]
          streamSource = stream["streamSource"]
          streamId = stream["streamId"]
          if streamName is not None:
            if streamSource == "TWITCH":
              streamUrl = f"https://www.twitch.tv/{streamName}"
            elif streamSource == "YOUTUBE":
              streamUrl = f"https://www.youtube.com/channel/{streamId}"
            else:
              streamUrl = f"{streamSource}: {streamName}"
        if streamUrl is not None:
          name1 = slot1["entrant"]["name"]
          name2 = slot2["entrant"]["name"]
          eventslug = event["slug"]
          slug = re.sub("/event/.+", "", eventslug)
          url = "https://www.start.gg/" + slug
          startsat = event["startAt"] or 0
          local_time = datetime.fromtimestamp(startsat, local_timezone)
          startsatstr = local_time.strftime(date_format)
          startday = local_time.strftime("%A")
          current_time = time.time()
          if current_time - startsat < recencyInterval:
            print(stream)
            res = cur.execute(f"SELECT setid FROM tourneyset WHERE setid = {setid}")
            result = res.fetchone()
            print(result)
            if result is None:
              setfoundtime = time.time()
              cur.executescript(f"INSERT INTO tourneyset VALUES({setfoundtime}, {setid})")
              print(name1 + " vs " + name2, fullRoundText, startsatstr, streamUrl, url, sep=', ')
              mention = roleMention
              header = f"## On Stream: {fullRoundText}"
              subtext1 = "-# Feel free to make a thread to provide unsolicited vod review and discussion or use the channel."
              subtext2 = "-# Don't @ someone after or during their set."
              subtext3 = "-# Don't @ a competitor with the feedback unless they're open to it"
              subtext4 = f"-# {subtextStr}"
              message = json.dumps({"content": f"{mention}\n{header}\n# **{name1}** vs **{name2}**\n{streamUrl}\n{url}\n{subtext1}\n{subtext2}\n{subtext3}\n{subtext4}"})
              r = requests.post(f"https://discordapp.com/api/channels/{discordChannelId}/messages", headers=discordHeaders, data=message)
              statuscode = r.status_code
              print(f"status code: {statuscode}")

