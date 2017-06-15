#!/usr/bin/env python3
import PIL.Image
import io
import json
import requests

import post_list
import web_cache


# Split this file into two modules, because we need to move web_cache out of
# the way between the two steps.  (We want to isolate the avatar HTTP requests)
# into its own thing.


def _make_avatar_url_list():
    seen = set()
    with open("avatar_urls", "wt") as fp:
        for post in post_list.load_posts():
            url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default" \
                  "?alt=json&v=2&orderby=published&reverse=false&max-results=1000" % post.postid
            js = json.loads(web_cache.get(url).decode("utf8"))
            for comment in js["feed"]["entry"]:
                (author,) = comment["author"]
                avatar = author["gd$image"]
                int(avatar["width"])
                int(avatar["height"])
                src = avatar["src"]
                if src not in seen:
                    seen.add(src)
                    assert "\n" not in src
                    fp.write(src + "\n")


def _fetch_avatar_urls():
    urls = open("avatar_urls", "r").read().splitlines()
    for i, url in enumerate(urls):
        print("[%d/%d] fetching %s ..." % (i + 1, len(urls), url))
        try:
            img = PIL.Image.open(io.BytesIO(web_cache.get(url)))
        except:
            print("WARNING: Bad avatar URL: %s" % url)


#_make_avatar_url_list()
_fetch_avatar_urls()
