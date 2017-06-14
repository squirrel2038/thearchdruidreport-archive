#!/usr/bin/env python3
import html
import json
import re
import threading
import xml.etree.ElementTree as ET

import web_cache
import util


# These HTTP requests are similar to those used by the blog's archive widget
# to download each month's posts.
def get_widget_posts():
    ret = []

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
            ret.append({"title_condensed": html.unescape(post["title"]), "url": post["url"]})

    return ret


def get_json_posts():
    ret = []

    for start in range(1, 600, 100):
        # Download the XML version too just to keep it around.  Maybe it'll
        # be useful someday.
        ET.fromstring(  web_cache.get("https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=atom&start-index=%d&max-results=100" % start).decode("utf8"))
        js = json.loads(web_cache.get("https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=json&start-index=%d&max-results=100" % start).decode("utf8"))

        for entry in js["feed"]["entry"]:

            title = entry["title"]["$t"]
            m = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", entry["id"]["$t"])
            postid = m.group(1)

            (link,) = [x for x in entry["link"] if x.get("rel") == "alternate"]
            title_link = link["title"]
            href = link["href"]

            m = re.match(r"http://thearchdruidreport\.blogspot\.com/(20../../.*\.html)$", link["href"])
            url = "https://thearchdruidreport.blogspot.com/" + m.group(1)

            ret.append({
                "title": title,
                "title_formatted": title_link,
                "url": url,
                "postid": postid,
            })

    return ret


def get_posts():
    posts = get_json_posts()
    postsW = get_widget_posts()
    assert len(posts) == len(postsW)
    for (p, pw) in zip(posts, postsW):
        assert p["url"] == pw["url"]
        p.update(pw)
    return posts


def main():
    all_posts = get_posts()
    util.set_file_text("posts.json", json.dumps(all_posts, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
