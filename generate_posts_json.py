#!/usr/bin/env python3
import html
import json
import re
import threading

import web_cache
import util

web_cache.set_fs_lock(threading.Lock())

# These HTTP requests are similar to those used by the blog's archive widget
# to download each month's posts.

all_posts = []

for year in range(2017, 2005, -1):
    data = web_cache.get("https://thearchdruidreport.blogspot.com/?action=getTitles&widgetId=BlogArchive1&widgetType=BlogArchive&responseType=js&path=http%3A%2F%2Fthearchdruidreport.blogspot.com%2F" + str(year))
    data = data.decode("utf8")

    # Extract the JSON-ish thing from the JS code.
    m = re.search(r"""_WidgetManager\._HandleControllerResult\('BlogArchive1', 'getTitles',(\{.*\})\);""", data)
    assert m
    data = m.group(1)

    # We don't have a JS parser, but we do have a JSON parser.  Hack the JS into
    # JSON.
    data = data.replace("\\x26", "&")
    assert '"' not in data
    assert '\\' not in data
    data = data.replace("'", '"')

    for post in json.loads(data)["posts"]:
        all_posts += [{"title": html.unescape(post["title"]), "url": post["url"]}]

util.set_file_text("posts.json", json.dumps(all_posts, indent=4, sort_keys=True))
