#!/usr/bin/env python3
#
# Consolidate all the raw Blogger JSON files into a single, simplified JSON file.
#

from collections import OrderedDict
import html
import io
import json
import sys
import lxml.etree as ET
import lxml.html
import re

import feeds
import util

posts = feeds.json_post_entries_list()

output = []

for jpost in posts:

    npost = OrderedDict()
    output.append(npost)

    npost["postid"] = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", jpost["id"]["$t"]).group(1)
    assert jpost["title"]["type"] == "text"
    npost["title"] = jpost["title"]["$t"]
    (link,) = [x for x in jpost["link"] if x["rel"] == "alternate"]
    npost["title_formatted"] = link["title"]
    m = re.match(r"http://thearchdruidreport\.blogspot\.com/(20../../.*\.html)$", link["href"])
    url = "https://thearchdruidreport.blogspot.com/" + m.group(1)
    npost["url"] = url

    npost["published"] = jpost["published"]["$t"]   # e.g.: 2017-03-08T13:28:00.001-08:00
    npost["updated"] = jpost["updated"]["$t"]       # e.g.: 2017-03-08T13:32:19.336-08:00

    assert jpost["content"]["type"] == "html"
    npost["content"] = jpost["content"]["$t"]
    npost["comments"] = []

    for jcomment in feeds.comments_json(npost["postid"]):

        ncomment = OrderedDict()
        npost["comments"].append(ncomment)

        ncomment["commentid"] = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", jcomment["id"]["$t"]).group(1)
        (author,) = jcomment["author"]
        ncomment["name"] = author["name"]["$t"]
        ncomment["profile"] = author["uri"]["$t"]

        avatar_url = author["gd$image"]["src"]
        avatar_size = (int(author["gd$image"]["width"]), int(author["gd$image"]["height"]))
        small_avatar = avatar_size[0] < 30 and avatar_size[1] < 30
        if small_avatar:
            if avatar_size == (16, 16) and avatar_url == "http://img1.blogblog.com/img/b16-rounded.gif":
                ncomment["avatar"] = {"type": "blogger"}
            elif avatar_size == (16, 16) and avatar_url == "http://img1.blogblog.com/img/openid16-rounded.gif":
                ncomment["avatar"] = {"type": "openid"}
            else:
                raise RuntimeError("Invalid avatar info on comment (%s/%s, %s, %s)" % (
                    npost["postid"], ncomment["commentid"], avatar_url, avatar_size))
        else:
            ncomment["avatar"] = {"type": "url", "size": avatar_size, "url": avatar_url}

        ncomment["published"] = jcomment["published"]["$t"]
        ncomment["updated"] = jcomment["updated"]["$t"]
        (display_time,) = [p for p in jcomment["gd$extendedProperty"] if p["name"] == "blogger.displayTime"]
        ncomment["display_time"] = display_time["value"]
        ncomment["comment_removed"] = (
            len([p for p in jcomment["gd$extendedProperty"] if
                    (p["name"], p["value"]) == ("blogger.contentRemoved", "true")]) > 0)

        related = [x for x in jcomment["link"] if x["rel"] == "related"]
        if len(related) > 0:
            (related,) = related
            related = re.match(r"http://www\.blogger\.com/feeds/27481991/\d+/comments/default/(\d+)\?v=2$", related["href"])
            ncomment["in_reply_to"] = related.group(1)
        else:
            ncomment["in_reply_to"] = None

        ncomment["title"] = jcomment["title"]["$t"]
        assert jcomment["content"]["type"] == "html"
        ncomment["content"] = jcomment["content"]["$t"]

        #html_parser = ET.HTMLParser()
        #html = ET.HTML(content)
        # doc = ET.parse(io.StringIO(content), html_parser)
        # print(type(doc))
        #print(ET.tostring(html))
        #e = lxml.html.fragment_fromstring(content, create_parent="p")
        #print(e)
        #break


util.set_file_text("blog.json", json.dumps(output, indent=2))
