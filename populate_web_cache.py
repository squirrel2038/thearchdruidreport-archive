#!/usr/bin/env python3
import json
import re
import time

import web_cache
import generate_pages

for p in generate_pages.load_posts():
    if not web_cache.has(p.url):
        web_cache.get(p.url)
        generate_pages.generate_single_post(p.url)

def _request(url):
    if not web_cache.has(url):
        web_cache.get(url)

for year in range(2006, 2018):
    _request("https://thearchdruidreport.blogspot.com/%04d/" % year)
    for month in range(1, 13):
        _request("https://thearchdruidreport.blogspot.com/%04d/%02d/" % (year, month))

# Use something like this on mobile to request comments.
# x = requests.get('https://thearchdruidreport.blogspot.com/feeds/739164683723753251/comments/default?alt=json&orderby=published&reverse=false&max-results=1000').json
