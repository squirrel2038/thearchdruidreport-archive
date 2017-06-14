#!/bin/sh
set -e

./generate_posts_json.py
./populate_web_cache.py
./generate_pages.py

rm -fr web_cache.7z
rm -fr thearchdruidreport-archive.7z

# XXX: Try using a higher -md setting maybe?  You must have enough RAM:
#    10 * max(<md-setting>, <total-uncompressed-size-of-input-files>)
7z a -mx=9 -md=200m web_cache.7z                  web_cache
7z a -mx=9 -md=200m thearchdruidreport-archive.7z thearchdruidreport-archive
