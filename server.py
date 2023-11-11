import asyncio
import json
import websockets
import html
import requests

# id keys set to 1. loaded with server and saved after every tweet grab.
TWEETS_SEEN = {}

with open('seen_tweets.txt', 'r') as f:
    if f.readable(): 
        for id in f.readlines():
            if id == '': continue
            # strip newlines if theyre there
            id = id.replace('\n', '')
            TWEETS_SEEN[id] = 1


TWITTER_USER_ID = ""
DID = ""
BEARER = ""
PDS = ""

with open('.config', 'r') as f:
    if not f.readable():
        print('no config')
        exit(1)
    for line in f.readlines():
        if len(line.split('=')) < 2:
            continue
        s = line.split('=')
        key, val = s[0], '='.join(s[1:])
        if key == "TWITTER_USER_ID":
            TWITTER_USER_ID = val
        elif key == "DID":
            DID = val
        elif key == "BEARER":
            BEARER = val
        elif key == "PDS":
            PDS = val

if [TWITTER_USER_ID, DID, BEARER].count("") > 0:
    print("config not set properly")
    exit(1)

def post_tweet_to_bluseky(tweet):
    payload = {
        "collection":"app.bsky.feed.post", "repo": DID, 
        "record":{ "text": tweet["text"], "langs":["en"], 
                  "createdAt":tweet["time"],"$type":"app.bsky.feed.post"}}
    for attachment in tweet["attachments"]:
        if not payload["record"].get("embed"):
            payload["record"]["embed"] = {"$type": "app.bsky.embed.images", "images": []}
            payload["record"]["embed"]["images"].append({"image": attachment["blob"], "alt": ""})
    res = requests.post(f'https://{PDS}/xrpc/com.atproto.repo.createRecord', headers={"authorization": f"Bearer {BEARER}"}, json=payload)
    print(res.status_code, res.text)
import uuid, io
def twitter_to_bluesky_attachment(url, mime="application/octet-stream"):
    with requests.get(url, stream=True) as r:
        if mime == "application/octet-stream":
            mime = r.headers.get("content-type")
        print("download done")
        dat = io.BytesIO(r.raw.read())
        print("uploading")
        with requests.post(f'https://{PDS}/xrpc/com.atproto.repo.uploadBlob', timeout=60, headers={"Authorization": f"Bearer {BEARER}", "Content-Type": f"{mime}"}, data=dat) as upload_res:
            print(upload_res.text, upload_res.status_code)
            j = upload_res.json()
            print("upload done")
            return j
def act_on_tweets(tweets):
    for tweet in tweets:
        try:
            print("tweet")
            lTweet = tweet["legacy"]
            if TWEETS_SEEN.get(lTweet["id_str"]) != None:
                continue
            # new tweet, save that
            TWEETS_SEEN[lTweet["id_str"]] = 1
            with open('seen_tweets.txt', 'a') as f:
                f.write(lTweet["id_str"]+"\n")
            # ignore any tweets not by us
            if TWITTER_USER_ID != lTweet["user_id_str"]:
                continue
            # create fancy qrt or just use tweet text
            tweet_text = html.unescape(lTweet["full_text"])
            if lTweet.get("retweeted_status_result") != None:
                # remove 'RT @handle: '
                tweet_text = ':'.join(tweet_text.split(":")[1:])[1:]
                tweet_text = f'♻️ https://twitter.com/@{lTweet["retweeted_status_result"]["result"]["core"]["user_results"]["result"]["legacy"]["screen_name"]}:\n{tweet_text}'
            if lTweet.get("is_quote_status") is True:
                link = lTweet["quoted_status_permalink"]["expanded"].replace("twitter.com", "vxtwitter.com")
                tweet_text = f'♻️💬 {link}:\n\n{tweet_text}'
            # parse media items
            attachments = []
            if lTweet["entities"].get("media") is not None:
                incompatible_media = False # videos aren't supported by bluesky, so we skip video posts. 
                for media in lTweet["entities"].get("media"):
                    print("getting attachment")
                    # remove attachment link from text
                    tweet_text = tweet_text.replace(media["url"], "").rstrip()
                    bestQuality = {"bitrate": 0, "url": ""}
                    if media["type"] == 'video':
                        print("video not supported, skipping.")
                        incompatible_media = True
                        # for variant in media["video_info"]["variants"]:
                        #     if variant.get("bitrate") != None and variant.get("bitrate") > bestQuality["bitrate"]:
                        #         bestQuality = variant
                        # urly = bestQuality["url"].split('?')[0]
                        # print(bestQuality["content_type"])
                        # attachments.append(twitter_to_bluesky_attachment(urly, mime=bestQuality["content_type"]))
                    if media["type"] == 'photo':
                        attachments.append(twitter_to_bluesky_attachment(media["media_url_https"]))
                    print("done getting attachment")
                if incompatible_media: continue
            # Rel Mon DD HH:MM:SS +0000 YYYY
            twitter_time = lTweet["created_at"]
            time_parts = twitter_time.split(" ")
            month_map = { k: v for k, v in zip(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                                               ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]) }
            bluesky_time = f"{time_parts[5]}-{month_map[time_parts[1]]}-{time_parts[2]}T{time_parts[3]}.000Z"
            tweet_obj = {"text": tweet_text, "attachments": attachments, "time": bluesky_time}
            print("posting")
            post_tweet_to_bluseky(tweet_obj)
        except Exception as E:
            print('exception! ',E)
        

def parse_tweets_from_usertweets_data(data):
    tweets = []
    # dear lord in heaven, save me for my sins
    for instruction in data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]:
        entries = None
        if instruction["type"] == "TimelineAddEntries":
            entries = instruction["entries"]
        if entries is None: continue
        for entry in entries:
            # remove non-tweet entries from timeline pop
            if "tweet" not in entry["entryId"]:
                continue
            tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
            tweets += [tweet]
    return tweets

async def handler(websocket, path):
    print("hi")
    data = await websocket.recv()
    try:
        # data sent should just be the UserTweets responses. attempt to parse that.
        tweets = parse_tweets_from_usertweets_data(json.loads(data))
        await websocket.send(f"OKAY;{len(tweets)};")
        act_on_tweets(tweets)
        print('done parsing tweet data')
    except Exception as E: # not valid json. bye
        await websocket.send("INVALID_USERTWEETS_VALUE;")

start_server = websockets.serve(handler, "localhost", 31352)
 
 
 
asyncio.get_event_loop().run_until_complete(start_server)
 
asyncio.get_event_loop().run_forever()