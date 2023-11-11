# SUPPORT IS NOT GUARENTEED, YOU ARE ON YOUR OWN.
## twitter to bluesky bridge
posts existing tweets to bluesky when you browse your own twitter profile. **does not support video posts or replies.**
## setup
set the following in `.config`
 - PDS (post `!jazbot whereami` and it'll reply with a domain), 
 - DID (in network tools, if you see a `at://did:plc:` when loading your profile extract only the `did:plc:STUFFHERE` part),
 - bluesky bearer (use network tab of dev tools and check authoriation header, do not include the word Bearer)
 - and twitter user id (open network tab, refresh on profile and check UserTweets config object)

install client.userscript.js with tampermonkey, run server.py, and scroll your profile on twitter (refresh it first to make sure the userscript sees your newest tweets)