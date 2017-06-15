#!/usr/bin/env python3

import os
import util
import subprocess
import sys
import re

import post_list

src_files = []
for arg in sys.argv[1:]:
    for (base, _, files) in os.walk(arg):
        src_files += [os.path.join(base, f) for f in files]
src_files = sorted(set(src_files))

post_id_to_key = {}
for p in post_list.load_posts():
    post_id_to_key[p.postid] = "%04d/%02d/%s/" % (p.year, p.month, p.page)

def file_key(path):
    m = re.match(r"web_cache/thearchdruidreport\.blogspot\.com/feeds/(\d+)/comments", path)
    if m:
        postid = m.group(1)
        return post_id_to_key.get(postid, "") + path
    m = re.match(r"web_cache/thearchdruidreport\.blogspot\.com/search-updated-max=(\d\d\d\d)-(\d\d)", path)
    if m:
        return "%s/%s/%s" % (m.group(1), m.group(2), path)
    path = path.replace("web_cache/thearchdruidreport.blogspot.com/", "")
    return path

# Sort the file list keeping duplicated content nearby to improve compression.
src_files.sort(key=file_key)
for path in src_files:
    print(path)
