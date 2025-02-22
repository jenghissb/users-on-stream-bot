from execute_query import excecute_query
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
sleepInterval = config["sleepInterval"]
recencyIntervalDays = config["recencyIntervalDays"]
startggToken = config["startggToken"]
discordBotToken = config["discordBotToken"]
discordChannelId = config["discordChannelId"]
startggHeaders = {"Authorization": f"Bearer {startggToken}"}
discordHeaders = {
  "Authorization": f"Bot {discordBotToken}",
  "Content-Type": "application/json"
}
setsPerPage = 40

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
  for key in userSlugs:
    names.append(key)
  for name in names:
    slug = userSlugs[name]
    querystrings.append(f'  slug{slug}:user(slug:"{slug}") {{')
    querystrings.append("    id")
    querystrings.append("    player{")
    querystrings.append("      id")
    querystrings.append("      gamerTag")
    querystrings.append("    }")
    querystrings.append("  }")
  querystrings.append("}")
  querystring = "\n".join(querystrings)
  print(querystring)
  data = string_query(querystring, {}, startggHeaders)
  print(data)
  if "data" not in data:
      print(data)
      time.sleep(sleepInterval)
      continue
  users = list(data["data"].values())
  print(users)
  time.sleep(sleepInterval)
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
    setsData = excecute_query("query_stream_sets.gql", {"pID": playerId, "tournamentList": eventIds, "perPage": setsPerPage, "page": 1}, startggHeaders)
    if setsData is None:
      time.sleep(sleepInterval)
      continue
    print("setsData", setsData)
    time.sleep(sleepInterval)
    if "data" not in setsData:
      setsData = excecute_query("query_stream_sets.gql", {"pID": playerId, "tournamentList": eventIds, "perPage": setsPerPage, "page": 1}, startggHeaders)
      time.sleep(sleepInterval)
    if "data" not in setsData:
      print("data not in setsData")
      time.sleep(sleepInterval)
      continue      
    numPages = setsData["data"]["player"]["sets"]["pageInfo"]["totalPages"]
    setNodes = setsData["data"]["player"]["sets"]["nodes"]
    local_timezone = tzlocal.get_localzone()
    date_format = '%Y-%m-%d %I:%M %p (%Z)'
    recencyInterval = 60*60*24*recencyIntervalDays #filters out active sets that were never reported
    for setNode in setNodes:
      print(setNode)
      winnerId = setNode["winnerId"]
      fullRoundText = setNode["fullRoundText"]
      slots = setNode["slots"]
      event = setNode["event"]
      wslot = slots[0]
      lslot = slots[1]
      setid = setNode["id"]
      if slots[1]["entrant"]["id"] == winnerId:
        wslot = slots[1]
        lslot = slots[0]
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
          name = wslot["entrant"]["name"]
          name2 = lslot["entrant"]["name"]
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
              print(name + " vs " + name2, fullRoundText, startsatstr, streamUrl, url, sep=', ')
              mention = "@Belmont Clan "
              header = f"## On Stream: {fullRoundText}"
              subtext1 = "-# Feel free to make a thread to provide unsolicited vod review and discussion or use the channel."
              subtext2 = "-# Don't @ someone after or during their set."
              subtext3 = "-# Don't @ a competitor with the feedback unless they're open to it"
              subtext4 = "-# Remember to be kind and respectful to fellow vanquishers of darkness"
              message = json.dumps({"content": f"{mention}\n{header}\n# **{name}** vs **{name2}**\n{streamUrl}\n{url}\n{subtext1}\n{subtext2}\n{subtext3}\n{subtext4}"})
              r = requests.post(f"https://discordapp.com/api/channels/{discordChannelId}/messages", headers=discordHeaders, data=message)
              statuscode = r.status_code
              print(f"status code: {statuscode}")

