# SUPPORT IS NOT GUARENTEED, YOU ARE ON YOUR OWN.
## twitter to bluesky bridge
posts existing tweets to bluesky when you browse your own twitter profile. **does not support video posts or replies.**
## setup
set your DID ( if you see a `at://did:plc:` when loading your profile extract only the `did:plc:STUFFHERE` part), bluesky bearer (use network tab of dev tools and check authoriation header, do not include the word Bearer), and twitter user id (something like https://tweeterid.com/ works) in `.config`
run server.py, install client.userscript.js with tampermonkey, and scroll your profile on twitter (refresh it to make sure the userscript sees your tweets)