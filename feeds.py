from datetime import datetime
import io
import json
import re
import lxml.etree as ET

import web_cache


def parse_timestamp(stamp):
    # Returns a local datetime with timezone information.
    m = re.match(r"(\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d\d\d[+-]\d\d):(\d\d)$", stamp)
    assert m
    ret = datetime.strptime(m.group(1) + m.group(2), "%Y-%m-%dT%H:%M:%S.%f%z")
    assert ret.tzinfo is not None
    return ret


def comments_xml(postid):
    # Return the XML feed document (lxml ElementTree) containing comments for
    # the given post ID, in order of publishing.
    url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default?orderby=published&reverse=false&max-results=1000" % postid
    parser = ET.XMLParser(remove_blank_text=True)
    return ET.parse(io.BytesIO(web_cache.get(url)), parser)


def comments_json(postid):
    url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default?alt=json&v=2&orderby=published&reverse=false&max-results=1000" % postid
    return json.loads(web_cache.get(url).decode("utf8"))


def get_xml_entry_publish_data(entry):
    assert entry.tag == "{http://www.w3.org/2005/Atom}entry"
    (published,) = entry.findall("{http://www.w3.org/2005/Atom}published")
    return parse_timestamp(published.text)


def get_xml_entry_id(entry):
    (entryid,) = entry.findall("{http://www.w3.org/2005/Atom}id")
    entryid = re.match(r"tag:blogger.com,1999:blog-27481991.post-(\d+)$", entryid.text)
    entryid = entryid.group(1)
    return entryid


def xml_post_entries_list():
    parser = ET.XMLParser(remove_blank_text=True)
    # Return a list of <entry> XML tags, in order of publishing, for every post.
    ret = []
    for start in range(1, 600, 100):
        url = "https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=atom&start-index=%d&max-results=100" % start
        posts = ET.parse(io.BytesIO(web_cache.get(url)), parser)
        posts = posts.getroot()
        ret += posts.findall("{http://www.w3.org/2005/Atom}entry")
    return ret[::-1]


def json_post_entries_list():
    # Return a list of all post JSON objects, in order of publishing.
    ret = []
    for start in range(1, 600, 100):
        url = "https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=json&start-index=%d&max-results=100" % start
        posts = json.loads(web_cache.get(url).decode("utf8"))
        posts = posts["feed"]["entry"]
        assert type(posts) is list
        ret += posts
    return ret[::-1]
