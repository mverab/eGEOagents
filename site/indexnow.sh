#!/usr/bin/env bash
# IndexNow submit — run after each deploy to ping Bing/Yandex with updated URLs.
KEY="f5a2fba5489afde386608045efc599e6"
HOST="egeoagents.com"
URLS=$(curl -s "https://$HOST/sitemap-0.xml" | grep -o '<loc>[^<]*</loc>' | sed 's/<[^>]*>//g')
python3 - "$KEY" "$HOST" $URLS <<'PY'
import json,sys,urllib.request
key,host=sys.argv[1],sys.argv[2]; urls=sys.argv[3:]
body=json.dumps({"host":host,"key":key,"keyLocation":f"https://{host}/{key}.txt","urlList":urls}).encode()
req=urllib.request.Request("https://api.indexnow.org/indexnow",data=body,headers={"Content-Type":"application/json"})
try:
    r=urllib.request.urlopen(req,timeout=30); print("IndexNow:",r.status,"—",len(urls),"URLs")
except Exception as e: print("IndexNow error:",e)
PY
