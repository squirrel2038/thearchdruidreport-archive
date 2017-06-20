#!/usr/bin/env python3
import PIL.Image
import io
import json
import re
import requests
import sys

import populate_web_cache
import post_list
import util
import web_cache


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
        populate_web_cache.add_image_to_web_cache(url, kind="avatar")


if sys.argv[1] == "list":
    _make_avatar_url_list()
if sys.argv[1] == "fetch":
    _fetch_avatar_urls()
