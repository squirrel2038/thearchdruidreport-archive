#!/usr/bin/env python3
#
# Parse the XML comments feed for each post and verify a few basic properties
# about the structure of the XML.
#

import io
import re
import xml.dom.minidom as MD

import feeds
import post_list
import web_cache
import util
import parallel


def _verify_post(postid):
    print("Verifying post %s" % postid)

    comments = feeds.comments_xml(postid)
    toplevel_comments = set()

    for c in comments.getElementsByTagName("entry"):

        (cid,) = c.getElementsByTagName("id")
        (cid,) = cid.childNodes
        cid = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", cid.data)
        cid = cid.group(1)

        # The <thr:in-reply-to> tag always refers to the postID, not to a
        # parent comment
        (orig,) = c.getElementsByTagName("thr:in-reply-to")
        orig = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", orig.getAttribute("ref"))
        orig = orig.group(1)
        assert orig == postid

        # A nested comment uses <link rel="related"> to refer to its parent
        # comment.  The nesting only goes one level deep.
        parent = [e for e in c.getElementsByTagName("link") if e.getAttribute("rel") == "related"]
        if len(parent) == 0:
            toplevel_comments.add(cid)
        else:
            (parent,) = parent
            parent = re.match(r"http://www.blogger.com/feeds/27481991/\d+/comments/default/(\d+)\?v=2$", parent.getAttribute("href"))
            parent = parent.group(1)
            # The parent ID is one we've already seen, and it was a toplevel
            # comment.
            assert parent in toplevel_comments


def main(apply_, flush):
    for post in post_list.load_posts():
        apply_(_verify_post, (post.postid,))


if __name__ == "__main__":
    parallel.run_main(main)
