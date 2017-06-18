#!/usr/bin/env python3
import PIL.Image
import io
import json
import re
import requests
import sys

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
    web_cache.set_cache_dir("web_cache_feed_avatars", "web_cache_feed_avatars_import")
    urls = open("avatar_urls", "r").read().splitlines()
    for i, url in enumerate(urls):
        print("[%d/%d] fetching %s ..." % (i + 1, len(urls), url))

        secure_url   = re.sub(r"([a-z]+:)?//", "https://", url)
        insecure_url = re.sub(r"([a-z]+:)?//", "http://", url)

        secure_bytes = None
        secure_image = None
        insecure_bytes = None
        insecure_image = None

        try:
            secure_bytes = web_cache.get(secure_url)
            if util.image_extension(secure_bytes):
                secure_image = PIL.Image.open(io.BytesIO(secure_bytes))
        except web_cache.ResourceNotAvailable:
            pass

        if secure_image is None or url.startswith("http://"):
            try:
                insecure_bytes = web_cache.get(insecure_url)
                if util.image_extension(insecure_bytes):
                    insecure_image = PIL.Image.open(io.BytesIO(insecure_bytes))
            except web_cache.ResourceNotAvailable:
                pass

        if not secure_image and not insecure_image:
            print("WARNING: Bad avatar URL: %s" % url)


if sys.argv[1] == "list":
    _make_avatar_url_list()
if sys.argv[1] == "fetch":
    _fetch_avatar_urls()
