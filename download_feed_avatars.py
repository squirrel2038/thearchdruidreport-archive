#!/usr/bin/env python3
import PIL.Image
import io
import json
import re
import requests
import sys

import feeds
import populate_web_cache
import post_list
import util
import web_cache


def _make_avatar_url_list():
    seen = set()
    with open("avatar_urls", "wt") as fp:
        for post in post_list.load_posts():
            for comment in feeds.comments_json(post.postid):
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
