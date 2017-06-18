import io
import json
import xml.dom.minidom as MD

import web_cache


_URL_TEMPLATE = "https://thearchdruidreport.blogspot.com/feeds/%(postid)s/comments/default?alt=%(format)s&v=2&orderby=published&reverse=false&max-results=1000"


def comments_xml(postid):
    url = _URL_TEMPLATE % {"postid": postid, "format": "atom"}
    return MD.parse(io.BytesIO(web_cache.get(url)))


def comments_json(postid):
    url = _URL_TEMPLATE % {"postid": postid, "format": "json"}
    return json.loads(web_cache.get(url).decode("utf8"))
