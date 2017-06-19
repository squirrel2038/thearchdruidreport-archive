#!/usr/bin/env python3
#
# Parse the XML comments feed for each post and verify a few basic properties
# about the structure of the XML.
#

from datetime import datetime
import io
import re
import lxml.etree as ET

import feeds
import post_list
import web_cache
import util
import parallel


def _verify_post(postid):
    print("Verifying post %s" % postid)

    comments = feeds.comments_xml(postid)
    toplevel_comments = set()
    curtime = feeds.parse_timestamp("1900-01-01T01:00:00.000+00:00")

    for c in comments.findall("{http://www.w3.org/2005/Atom}entry"):

        cid = feeds.get_xml_entry_id(c)

        # The <thr:in-reply-to> tag always refers to the postID, not to a
        # parent comment
        (orig,) = c.findall("{http://purl.org/syndication/thread/1.0}in-reply-to")
        orig = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", orig.attrib["ref"])
        orig = orig.group(1)
        assert orig == postid

        published = feeds.get_xml_entry_publish_data(c)
        assert published > curtime
        curtime = published

        # A nested comment uses <link rel="related"> to refer to its parent
        # comment.  The nesting only goes one level deep.
        parent = [e for e in c.findall("link") if e.attrib["rel"] == "related"]
        if len(parent) == 0:
            toplevel_comments.add(cid)
        else:
            (parent,) = parent
            parent = re.match(r"http://www.blogger.com/feeds/27481991/\d+/comments/default/(\d+)$", parent.attrib["href"])
            parent = parent.group(1)
            # The parent ID is one we've already seen, and it was a toplevel
            # comment.
            assert parent in toplevel_comments


def main(apply_, flush):
    for post in post_list.load_posts():
        apply_(_verify_post, (post.postid,))


if __name__ == "__main__":
    parallel.run_main(main)
