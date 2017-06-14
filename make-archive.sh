#!/bin/sh
#
# If you have 10GB of free RAM, use this command-line:
#    (time TADR_WEB_CACHE_7Z_OPTS=-md=1000m ./make-archive.sh) >& LOG
#
set -e

rm -fr web_cache.7z
rm -fr thearchdruidreport-archive.7z

./generate_posts_json.py
./populate_web_cache.py
./generate_pages.py

7z a -mx=9 thearchdruidreport-archive.7z thearchdruidreport-archive
7z a -mx=9 ${TADR_WEB_CACHE_7Z_OPTS} web_cache.7z web_cache

# For a smaller web_archive.7z, set
#     TADR_WEB_CACHE_7Z_OPTS to -md=1000m
# You'll need 10GB of RAM to compress, then 1GB to decompress.  The total
# compression RAM requirement is:
#     10 * max(<md-setting>, <total-uncompressed-size-of-input-files>)
# If you don't have enough free RAM, then 7z exits with a cryptic error:
#     System error:
#     E_INVALIDARG
