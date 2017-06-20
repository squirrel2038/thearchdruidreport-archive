#!/usr/bin/env python3
from collections import OrderedDict
import json
import re
import sys

import generate_pages
import parallel
import util


BLOG_JSON = json.loads(util.get_file_text("blog.json"))


def json_avatar_fields(comment):
    ret = {}
    avatar = comment["avatar"]
    if avatar["type"] in ("blogger", "openid"):
        ret[100] = avatar["type"]
        ret[500] = "n/a"
    elif avatar["type"] == "url":
        url = avatar["url"]
        if url.startswith("//"):
            url = "https:" + url
        ret[100] = '<img src="%s" style="max-width: 35px;">' % url
        ret[500] = repr(avatar["size"])
    return ret


def html_avatar_fields(comment):
    ret = {}
    url = comment.avatar_url
    if url.startswith("//"):
        url = "https:" + url
    ret[101] = '<img src="%s" width="%d" height="%d">' % (
        url, comment.avatar_size[0], comment.avatar_size[1])
    ret[501] = repr(comment.avatar_size)
    return ret


def main(apply_, flush):
    json_posts = BLOG_JSON

    post_html_comments = []
    post_mobile_comments = []
    for post in json_posts:
        post_html_comments.append(apply_(generate_pages.get_comments, (post["url"],)))
        post_mobile_comments.append(apply_(generate_pages.get_mobile_comments, (post["url"],)))

    rows = OrderedDict()
    for (post, html_comments, mobile_comments) in zip(json_posts, post_html_comments, post_mobile_comments):
        print("Checking avatars for %s ..." % post["url"])
        sys.stdout.flush()
        html_comments = html_comments.get()
        mobile_comments = mobile_comments.get()
        mobile_comments = {m.id[1:]: m for m in mobile_comments}
        assert len(post["comments"]) == len(html_comments)
        assert len(post["comments"]) == len(mobile_comments)
        for jc, hc in zip(post["comments"], html_comments):
            assert jc["commentid"] == hc.id[1:]
            # With a few exceptions (where there is no avatar at all), the
            # avatar URLs for the desktop and mobile sites are equal.
            if hc.avatar_url != mobile_comments[jc["commentid"]].avatar_url:
                print("MISMATCH DESKTOP/MOBILE %s %s#c%s" % (post["postid"], post["url"], jc["commentid"]))
                print("desktop:", hc.avatar_url)
                print("mobile: ", mobile_comments[jc["commentid"]].avatar_url)
                print("feed:   ", repr(jc["avatar"]))
                print("---")
            row = {}
            row.update(json_avatar_fields(jc))
            row.update(html_avatar_fields(hc))
            row = [row[k] for k in sorted(row.keys())]
            key = repr(row)
            insecure_url = re.sub(r"^https://", "http://", post["url"])
            row.append('<a href="%s#c%s">Desktop</a>' % (insecure_url, jc["commentid"]))
            row.append('<a href="%s#c%s">DesktopSSL</a>' % (post["url"], jc["commentid"]))
            row.append('<a href="%s?m=1#c%s">Mobile</a>' % (insecure_url, jc["commentid"]))
            row.append('<a href="%s?m=1#c%s">MobileSSL</a>' % (post["url"], jc["commentid"]))
            row = "<tr><td>" + "</td><td>".join(row) + "</td></tr>\n"
            if key not in rows:
                rows[key] = row

    util.set_file_text("avatar_survey.html", """<!DOCTYPE html>
<html>
    <body>
        <table>
""" + \
"".join(rows.values()) + \
"""
        </table>
    </body>
</html>
""")


if __name__ == "__main__":
    parallel.run_main(main)
