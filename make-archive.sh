#!/bin/sh
set -e

./generate_posts_json.py
./generate_pages.py
./populate_web_cache.py

for name in web_cache the-archdruid-report; do
    rm -f $name.tar.xz
    XZ_OPT='-v9' tar cfJ $name.tar.xz --owner=0 --group=0 $name
done
