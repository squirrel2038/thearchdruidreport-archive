#!/bin/sh
set -e

./generate_posts_json.py
./populate_web_cache.py
./generate_pages.py

for name in web_cache thearchdruidreport-archive; do
    rm -f $name.7z
    7z a -mx=9 $name.tar.xz $name
done
