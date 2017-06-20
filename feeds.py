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


def comments_url(postid, kind=None, ver=None, start=None, max_results=None):
    # The `start` index starts at 1, not 0, because that's the convention
    # the Blogger URL uses.
    url = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default" % postid
    params = []
    if kind is not None:
        params.append("alt=%s" % kind)
    if ver is not None:
        params.append("v=%d" % ver)
    params.append("orderby=published")
    params.append("reverse=false")
    if start is not None:
        params.append("start-index=%d" % start)
    if max_results is not None:
        params.append("max-results=%d" % max_results)
    return url + "?" + "&".join(params)


def comments_xml(postid, kind=None, ver=None):
    # Return a list of <entry> tags for the given post ID, in order of
    # publishing.
    ret = []
    for start in range(1, 1000, 250):
        url = comments_url(postid, kind=kind, ver=ver, start=start, max_results=250)
        doc = ET.parse(io.BytesIO(web_cache.get(url)))
        batch = doc.findall("{http://www.w3.org/2005/Atom}entry")
        ret += batch
        if len(batch) < 250:
            break
    return ret


def comments_json(postid):
    ret = []
    for start in range(1, 1000, 250):
        url = comments_url(postid, kind="json", ver=2, start=start, max_results=250)
        doc = json.loads(web_cache.get(url).decode("utf8"))
        batch = doc["feed"].get("entry", [])
        assert type(batch) is list
        ret += batch
        if len(batch) < 250:
            break
    return ret


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
