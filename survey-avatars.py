#!/usr/bin/env python3
from collections import OrderedDict
import PIL.Image
import io
import json
import re
import sys

import generate_pages
import parallel
import util
import web_cache


BLOG_JSON = json.loads(util.get_file_text("blog.json"))
_pil_image_cache = {}


def _pil_image(url):
    global _pil_image_cache
    if url not in _pil_image_cache:
        _pil_image_cache[url] = PIL.Image.open(io.BytesIO(web_cache.get(url)))
    return _pil_image_cache[url]


def json_avatar_fields(comment):
    ret = {}
    avatar = comment["avatar"]
    if avatar["type"] in ("blogger", "openid"):
        ret["0-img-a"] = avatar["type"]
        ret["1-siz-a"] = "n/a"
        ret["2-author"] = ""
    elif avatar["type"] == "url":
        url = avatar["url"]
        if url.startswith("//"):
            url = "https:" + url
        ret["0-img-a"] = '<img src="%s" style="max-width: 35px;">' % url
        ret["1-siz-a"] = repr(avatar["size"])
        ret["2-author"] = comment["author"]
        assert avatar["size"][0] <= 34
        assert avatar["size"][1] <= 32
    return ret


def html_avatar_fields(comment):
    ret = {}
    url = comment.avatar_url
    if url.startswith("//"):
        url = "https:" + url
    ret["0-img-b"] = '<img src="%s" width="%d" height="%d">' % (
        url, comment.avatar_size[0], comment.avatar_size[1])
    ret["1-siz-b"] = repr(comment.avatar_size)
    true_size = "n/a"
    try:
        if url:
            img_data = web_cache.get(url)
            if util.image_extension(img_data):
                true_size = str(_pil_image(url).size)
    except web_cache.ResourceNotAvailable:
        pass
    ret["3-html-size"] = true_size
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
            if "url" in jc["avatar"]:
                row["4-html-match"] = ["", "REUSES_ORIG_URL"][
                    re.sub(r"^https?:", "", jc["avatar"]["url"]) ==
                    re.sub(r"^https?:", "", hc.avatar_url)]
            else:
                row["4-html-match"] = ""
            row = [row[k] for k in sorted(row.keys())]
            key = repr(row)
            insecure_url = re.sub(r"^https://", "http://", post["url"])
            row.append('<a href="%s#c%s">Desktop</a>' % (insecure_url, jc["commentid"]))
            row.append('<a href="%s#c%s">DesktopSSL</a>' % (post["url"], jc["commentid"]))
            row.append('<a href="%s?m=1#c%s">Mobile</a>' % (insecure_url, jc["commentid"]))
            row.append('<a href="%s?m=1#c%s">MobileSSL</a>' % (post["url"], jc["commentid"]))
            month = str(re.search(r"/(\d\d\d\d/\d\d)/", post["url"]).group(1))
            row.append(month)
            row.append(month)
            if key not in rows:
                rows[key] = row
            else:
                rows[key] = rows[key][:-1] + [month]


    util.set_file_text("avatar_survey.html", """<!DOCTYPE html>
<html>
    <body>
        <table>
""" + \
"".join([("<tr><td>" + "</td><td>".join(row) + "</td></tr>") for row in rows.values()]) + \
"""
        </table>
    </body>
</html>
""")


if __name__ == "__main__":
    parallel.run_main(main)
