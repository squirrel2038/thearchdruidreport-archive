from datetime import datetime
import io
import json
import re
import xml.dom.minidom as MD

import web_cache


def parse_timestamp(stamp):
    # Returns a local datetime with timezone information.
    m = re.match(r"(\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d\d\d[+-]\d\d):(\d\d)$", stamp)
    assert m
    ret = datetime.strptime(m.group(1) + m.group(2), "%Y-%m-%dT%H:%M:%S.%f%z")
    assert ret.tzinfo is not None
    return ret


def comments_xml(postid):
    # Return the XML feed document containing comments for the given post ID,
    # in order of publishing.
    url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default?orderby=published&reverse=false&max-results=1000" % postid
    return MD.parseString(web_cache.get(url).decode("utf8"))


def comments_json(postid):
    url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default?alt=json&v=2&orderby=published&reverse=false&max-results=1000"
    return json.loads(web_cache.get(url).decode("utf8"))


def get_xml_entry_publish_data(entry):
    assert entry.tagName == "entry"
    (published,) = entry.getElementsByTagName("published")
    (published,) = published.childNodes
    return parse_timestamp(published.data)


def get_xml_entry_id(entry):
    (entryid,) = entry.getElementsByTagName("id")
    (entryid,) = entryid.childNodes
    entryid = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", entryid.data)
    entryid = entryid.group(1)
    return entryid


def xml_post_entries_list():
    # Return a list of <entry> XML tags, in order of publishing, for every post.
    ret = []
    for start in range(1, 600, 100):
        posts = MD.parse(io.BytesIO(web_cache.get("https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=atom&start-index=%d&max-results=100" % start)))
        for post in posts.getElementsByTagName("entry"):
            ret.append(post)
    return ret[::-1]
