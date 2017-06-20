#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta
import json
import re
import sys
import traceback

import feeds
import util
import web_cache


BLOG_POSTS = json.loads(util.get_file_text("blog.json"))

for post in BLOG_POSTS:
    page_count = (len(post["comments"]) + 199) // 200
    print("DEBUG:", post["url"], len(post["comments"]), page_count)
    for page in range(1, page_count + 1):
        url = post["url"] if page == 1 else ("%s?commentPage=%d" % (post["url"], page))
        print("DEBUG:", url)
        obj = json.loads(web_cache.get("https://archive.org/wayback/available?url=" + url).decode("utf8"))
        try:
            snap = obj["archived_snapshots"]["closest"]
            assert snap["available"] == True
            assert snap["status"] == "200"
            ts = re.match(r"^(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)$", snap["timestamp"])
            assert ts
            m = re.match(r"^http://web\.archive\.org/web/(\d+)/https?:(//.*)$", snap["url"])
            if not m:
                print(snap["url"])
                assert False
            assert m.group(1) == snap["timestamp"]
            assert m.group(2) == re.sub(r"^https://", "//", url)

            comment_latest = feeds.parse_timestamp(post["comments"][-1]["updated"])
            archive_latest = datetime(*[int(ts.group(i)) for i in range(1, 7)], tzinfo=timezone.utc)

            if archive_latest - comment_latest < timedelta(days=3):
                print("WARNING: archive is recent:", (archive_latest - comment_latest))

        except:
            sys.stdout.write("WARNING: EXCEPTION RAISED: ")
            traceback.print_exc(file=sys.stdout)
