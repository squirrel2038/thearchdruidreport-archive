#!/usr/bin/env python3
from bs4 import BeautifulSoup
import PIL.Image
import json
import io
import posixpath
import re
import sys
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET

import parallel
import web_cache
import post_list


_page_cache = {}
_pil_image_cache = {}


def _page(url):
    global _page_cache
    if url not in _page_cache:
        _page_cache[url] = BeautifulSoup(web_cache.get(url), "lxml")
    return _page_cache[url]


def _pil_image(url):
    global _pil_image_cache
    if url not in _pil_image_cache:
        _pil_image_cache[url] = PIL.Image.open(io.BytesIO(web_cache.get(url)))
    return _pil_image_cache[url]


def _fetch_year_month_queries():
    for year in range(2006, 2018):
        web_cache.get("https://thearchdruidreport.blogspot.com/%04d/" % year)
        for month in range(1, 13):
            web_cache.get("https://thearchdruidreport.blogspot.com/%04d/%02d/" % (year, month))


def _fetch_stylesheet_resources(css, base_url):
    i = 0
    p1 = re.compile(r"url\(")
    p2 = re.compile(r"url\(\"([^\%()\\\"\']+)\"\)")
    p3 = re.compile(r"url\(\'([^\%()\\\"\']+)\'\)")
    p4 = re.compile(r"url\(([^\%()\\\"\']+)\)")
    while True:
        s = p1.search(css, i)
        if s is None:
            break
        i = s.start()
        m = p2.match(css, i) or p3.match(css, i) or p4.match(css, i)
        url = m.group(1)
        if url.startswith("data:"):
            pass
        else:
            url = urllib.parse.urljoin(base_url, url)
            web_cache.get(url)
        i = m.end()


def _fetch_page_resources(url):
    doc = _page(url)
    for img in doc.find_all("img"):
        assert "delayLoad" not in img.attrs.get("class", [])
        assert "longdesc" not in img.attrs
        try:
            web_cache.get(urllib.parse.urljoin(url, img.attrs["src"]))
        except web_cache.ResourceNotAvailable:
            pass

        # As in generate_pages.py, if we have an image linking to a another
        # (i.e. bigger) Blogspot image, cache the linked image.  (This step
        # doesn't seem to do anything, because generate_pages.py already cached
        # everything.)
        if img.parent.name == "a" and "href" in img.parent.attrs:
            href = img.parent.attrs["href"]
            if re.match(r"(https?:)?//[1234]\.bp\.blogspot\.com/.*\.(png|gif|jpg|jpeg)$", href, re.IGNORECASE):
                web_cache.get(href)

    for link in doc.find_all("link"):
        rel = link.attrs["rel"]
        href = link.attrs["href"]
        href = urllib.parse.urljoin(url, href)
        if rel == "stylesheet":
            _fetch_stylesheet_resources(web_cache.get(href).decode("utf8"), href)
        if link.attrs["rel"] == "icon":
            web_cache.get(href)
    for script in doc.find_all("script"):
        if "src" in script.attrs:
            web_cache.get(urllib.parse.urljoin(url, script.attrs["src"]))
    for style in doc.find_all("style"):
        assert len(style.contents) == 1
        assert style.contents[0].name is None
        _fetch_stylesheet_resources(str(style.contents[0].string), url)


def _crawl_mobile_post_listings(apply_, flush):
    print("Crawling mobile post listings...")
    sys.stdout.flush()
    url = "https://thearchdruidreport.blogspot.com/?m=1"
    while url is not None:
        doc = _page(url)
        apply_(_fetch_page_resources, (url,))
        next_anchor = doc.select("a.blog-pager-older-link")
        if len(next_anchor) == 0:
            url = None
        else:
            (next_anchor,) = next_anchor
            url = next_anchor.attrs["href"]
    flush()


def _crawl_mobile_post(url):
    print("Crawling %s ..." % url)
    sys.stdout.flush()
    _fetch_page_resources(url)


def _crawl_mobile_posts(apply_, flush):
    for p in post_list.load_posts():
        apply_(_crawl_mobile_post, (p.url + "?m=1",))
    flush()


def _download_comments_feed(url):
    print("Crawling %s Atom comments feed..." % url)
    doc = _page(url + "?m=1")
    post_id = doc.find("meta", itemprop="postId").attrs["content"]
    atom_feed = "https://thearchdruidreport.blogspot.com/feeds/%s/comments/default" % post_id
    # Get both the JSON version and the Atom XML version.  Make sure they parse.
    ET.fromstring(  web_cache.get(atom_feed + "?alt=atom&v=2&orderby=published&reverse=false&max-results=1000"))
    js = json.loads(web_cache.get(atom_feed + "?alt=json&v=2&orderby=published&reverse=false&max-results=1000").decode("utf8"))
    # These avatar images are special, because they're full-size.  Images
    # sourced from Blogger's HTML files are usually (but not always!) shrunk
    # to under 35x35.  Maybe it'd be nice to downlod these full-size images and
    # provide sharper avatars for retina displays, but I think it'd make the
    # web_cache much bigger.  Leave them out, at least for now.
    if False:
        for comment in js["feed"]["entry"]:
            (author,) = comment["author"]
            avatar = author["gd$image"]
            int(avatar["width"])
            int(avatar["height"])
            try:
                img = _pil_image(avatar["src"])
            except:
                print("WARNING: Bad avatar URL: %s" % avatar["src"])


def _download_comments_feeds(apply_, flush):
    for p in post_list.load_posts():
        apply_(_download_comments_feed, (p.url,))
    flush()


def _download_posts_bare():
    count = 0
    for start in range(1, 600, 100):
        ET.fromstring(  web_cache.get("https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=atom&start-index=%d&max-results=100" % start).decode("utf8"))
        js = json.loads(web_cache.get("https://thearchdruidreport.blogspot.com/feeds/posts/default?alt=json&start-index=%d&max-results=100" % start).decode("utf8"))
        for entry in js["feed"]["entry"]:
            count += 1
    assert count == len(post_list.load_posts())


def _main(apply_, flush):
    for url in [
            # There are two desktop pages for viewing comments -- the main
            # read-only page and a special white-backgrounded page for entering
            # and viewing comments.  For 2013/01/into-unknown-country.html,
            # this is the URL for the latter (two pages):
            "https://www.blogger.com/comment.g?blogID=27481991&postID=5625187186942053195",
            "https://www.blogger.com/comment.g?postID=5625187186942053195&blogID=27481991&isPopup=false&page=2",
            # This is a comments page where there is a reply:
            #  - desktop URL: http://thearchdruidreport.blogspot.com/2017/03/the-magic-lantern-show.html
            "https://www.blogger.com/comment.g?blogID=27481991&postID=1891285484434881454",
        ]:
        _fetch_page_resources(url)

    _fetch_year_month_queries()
    _crawl_mobile_post_listings(apply_, flush)
    _crawl_mobile_posts(apply_, flush)
    _download_comments_feeds(apply_, flush)
    _download_posts_bare()


if __name__ == "__main__":
    parallel.run_main(_main)


# Use something like this on mobile to request comments.
# x = requests.get('https://thearchdruidreport.blogspot.com/feeds/739164683723753251/comments/default?alt=json&v=2&orderby=published&reverse=false&max-results=1000').json


# This page has a reply, 125 comments
#  - http://thearchdruidreport.blogspot.com/2017/03/the-magic-lantern-show.html?m=1
# This comment is a reply, but you can't tell on the desktop site:
#  - http://thearchdruidreport.blogspot.com/2017/03/the-magic-lantern-show.html?showComment=1488647590675&m=1#c3012836938846340532
#  - http://thearchdruidreport.blogspot.com/2017/03/the-magic-lantern-show.html?showComment=1488647590675#c3012836938846340532
# Links for this page:
#   <link rel="alternate" type="application/atom+xml" title="The Archdruid Report - Atom" href="http://thearchdruidreport.blogspot.com/feeds/posts/default" />
#   <link rel="alternate" type="application/rss+xml" title="The Archdruid Report - RSS" href="http://thearchdruidreport.blogspot.com/feeds/posts/default?alt=rss" />
#   <link rel="service.post" type="application/atom+xml" title="The Archdruid Report - Atom" href="https://www.blogger.com/feeds/27481991/posts/default" />
#   <link rel="alternate" type="application/atom+xml" title="The Archdruid Report - Atom" href="http://thearchdruidreport.blogspot.com/feeds/1891285484434881454/comments/default" />
