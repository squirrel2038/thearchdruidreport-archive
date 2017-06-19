#!/usr/bin/env python3
from copy import deepcopy
import io
import re
import lxml.etree as ET

import feeds
import web_cache
import util


ARCHIVE_XML_BASE = """<?xml version="1.0" encoding="UTF8"?>
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
""".encode("utf8")


def _set_entry_category(entry, category):
    (insert_point,) = entry.findall("{http://www.w3.org/2005/Atom}title")
    assert insert_point.getprevious().tag == "{http://www.w3.org/2005/Atom}updated"
    entry.insert(entry.index(insert_point), deepcopy(category))


def _generate_file(is_sample):
    category_post    = ET.XML('<category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#post"/>')
    category_comment = ET.XML('<category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#comment"/>')

    parser = ET.XMLParser(remove_blank_text=True)
    doc = ET.parse(io.BytesIO(ARCHIVE_XML_BASE), parser)
    feed = doc.getroot()

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

        post = deepcopy(post)
        published = feeds.get_xml_entry_publish_data(post)
        _set_entry_category(post, category_post)
        post_entries.append(post)

        comments = feeds.comments_xml(postid)
        for i, comment in enumerate(comments.findall("{http://www.w3.org/2005/Atom}entry")):
            comment = deepcopy(comment)
            published = feeds.get_xml_entry_publish_data(comment)
            _set_entry_category(comment, category_comment)
            comment_entries.append(((published, i), comment))

    # Insert all posts up-front, in reverse publishing order.
    for entry in post_entries[::-1]:
        feed.append(entry)

    # Insert comments from all combined posts, in publishing order.
    assert len({sortkey for sortkey, _ in comment_entries}) == len(comment_entries)
    comment_entries.sort()
    for _, entry in comment_entries:
        feed.append(entry)


    if is_sample:
        doc.write("blogger_export_sample.xml", xml_declaration=True, encoding="utf-8", pretty_print=True)
    else:
        doc.write("blogger_export.xml", xml_declaration=True, encoding="utf-8", pretty_print=True)


def _main():
    _generate_file(True)
    _generate_file(False)


if __name__ == "__main__":
    _main()
