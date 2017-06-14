#!/usr/bin/env python3
from bs4 import BeautifulSoup
import json
import posixpath
import re
import sys
import threading
import time
import urllib.parse

import web_cache
import generate_pages

web_cache.set_fs_lock(threading.Lock())
_page_cache = {}

def _page(url):
    global _page_cache
    if url not in _page_cache:
        _page_cache[url] = BeautifulSoup(web_cache.get(url), "lxml")
    return _page_cache[url]

def _fetch_year_month_queries():
    for year in range(2006, 2018):
        web_cache.get("https://thearchdruidreport.blogspot.com/%04d/" % year)
        for month in range(1, 13):
            web_cache.get("https://thearchdruidreport.blogspot.com/%04d/%02d/" % (year, month))

def _fetch_stylesheet_resources(css, base_url):
    i = 0
    p1 = re.compile(r"url\(")
    p2 = re.compile(r"url\(\"([^\%\&()\\\"\']+)\"\)")
    p3 = re.compile(r"url\(\'([^\%\&()\\\"\']+)\'\)")
    p4 = re.compile(r"url\(([^\%\&()\\\"\']+)\)")
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

def _crawl_mobile_post_listings():
    url = "https://thearchdruidreport.blogspot.com/?m=1"
    while url is not None:
        print("Crawling %s ..." % url)
        sys.stdout.flush()
        _fetch_page_resources(url)
        doc = _page(url)
        next_anchor = doc.select("a.blog-pager-older-link")
        if len(next_anchor) == 0:
            url = None
        else:
            (next_anchor,) = next_anchor
            url = next_anchor.attrs["href"]

def _crawl_mobile_posts():
    for p in generate_pages.load_posts():
        print("Crawling %s ..." % p.url)
        sys.stdout.flush()
        _fetch_page_resources(p.url + "?m=1")

def main():
    _fetch_year_month_queries()
    _crawl_mobile_post_listings()
    _crawl_mobile_posts()

if __name__ == "__main__":
    main()

# Use something like this on mobile to request comments.
# x = requests.get('https://thearchdruidreport.blogspot.com/feeds/739164683723753251/comments/default?alt=json&orderby=published&reverse=false&max-results=1000').json
