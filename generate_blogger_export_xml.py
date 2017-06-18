#!/usr/bin/env python3
import io
import re
import xml.dom.minidom as MD

import feeds
import web_cache
import util


ARCHIVE_XML_BASE = """<?xml version="1.0" ?>
<?xml-stylesheet href="http://www.blogger.com/styles/atom.css" type="text/css"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:gd="http://schemas.google.com/g/2005" xmlns:georss="http://www.georss.org/georss" xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/" xmlns:thr="http://purl.org/syndication/thread/1.0">
    <id>tag:blogger.com,1999:blog-27481991</id>
    <title type="text">The Archdruid Report</title>
    <subtitle type="html">Druid perspectives on nature, culture, and the future of industrial society</subtitle>
    <link href="https://www.blogger.com/feeds/27481991/archive" rel="http://schemas.google.com/g/2005#feed" type="application/atom+xml"/>
    <link href="https://www.blogger.com/feeds/27481991/archive" rel="self" type="application/atom+xml"/>
    <link href="https://www.blogger.com/feeds/27481991/archive" rel="http://schemas.google.com/g/2005#post" type="application/atom+xml"/>
    <link href="http://thearchdruidreport.blogspot.com/" rel="alternate" type="text/html"/>
    <author>
        <name>John Michael Greer</name>
        <email>noreply@blogger.com</email>
        <gd:image height="32" rel="http://schemas.google.com/g/2005#thumbnail" src="http://3.bp.blogspot.com/_l8lHlfw_Vps/TNL9uXoNBwI/AAAAAAAAABA/gr9jJgKhTxA/S220/JMG1.jpg" width="22"/>
    </author>
    <generator uri="http://www.blogger.com" version="7.00">Blogger</generator>
</feed>
"""


def set_entry_category(entry, category):
    (insert_point,) = entry.getElementsByTagName("updated")
    insert_point = insert_point.nextSibling
    assert insert_point.tagName == "title"
    entry.insertBefore(category.cloneNode(True), insert_point)


def _generate_file(is_sample):
    (category_post,)    = MD.parseString('<category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#post"/>').getElementsByTagName("category")
    (category_comment,) = MD.parseString('<category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#comment"/>').getElementsByTagName("category")

    doc = MD.parseString("".join(x.strip() for x in ARCHIVE_XML_BASE.splitlines()))
    (feed,) = doc.getElementsByTagName("feed")

    post_entries = []
    comment_tasks = []
    comment_entries = []

    for post in feeds.xml_post_entries_list():
        postid = feeds.get_xml_entry_id(post)

        if is_sample and postid not in [
                    "1891285484434881454", # https://thearchdruidreport.blogspot.com/2017/03/the-magic-lantern-show.html
                    "739164683723753251",  # https://thearchdruidreport.blogspot.com/2017/03/how-should-we-then-live.html
                    "5178643773481630823", # https://thearchdruidreport.blogspot.com/2017/05/a-brief-announcement.html
                ]:
            continue

        post = post.cloneNode(True)
        published = feeds.get_xml_entry_publish_data(post)
        set_entry_category(post, category_post)
        comment_entries.append(((published, 0), post))

        comments = feeds.comments_xml(postid)
        for i, comment in enumerate(comments.getElementsByTagName("entry")):
            comment = comment.cloneNode(True)
            published = feeds.get_xml_entry_publish_data(comment)
            set_entry_category(comment, category_comment)
            comment_entries.append(((published, i), comment))

    # Insert all posts up-front, in reverse publishing order.
    for entry in post_entries[::-1]:
        feed.appendChild(entry)

    # Insert comments from all combined posts, in publishing order.
    assert len({sortkey for sortkey, _ in comment_entries}) == len(comment_entries)
    comment_entries.sort()
    for _, entry in comment_entries:
        feed.appendChild(entry)

    if is_sample:
        util.set_file_text("blogger_export_sample.xml", doc.toprettyxml())
    else:
        util.set_file_text("blogger_export.xml", doc.toprettyxml())
        util.set_file_text("blogger_export.condensed.xml", doc.toxml())


def _main():
    _generate_file(True)
    _generate_file(False)


if __name__ == "__main__":
    _main()
