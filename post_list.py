import json
import re

import util


def parse_tar_url(url):
    m = re.match(r"^https://thearchdruidreport.blogspot.com/(20\d\d)/(\d\d)/(.+[.]html)$", url)
    year = int(m.group(1))
    month = int(m.group(2))
    page = m.group(3)
    return year, month, page


class Post:
    def __init__(self):
        pass

def load_posts():
    ret = []
    posts_json = json.loads(util.get_file_text("posts.json"))
    for post in posts_json:
        e = Post()
        e.postid = post["postid"]
        e.title = post["title"]
        e.title_condensed = post["title_condensed"]
        e.url = post["url"]
        e.year, e.month, e.page = parse_tar_url(e.url)
        ret.append(e)
    return ret
