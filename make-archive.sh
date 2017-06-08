#!/bin/sh
set -e

./generate_posts_json.py
./generate_pages.py
./populate_web_cache.py

rm -f web_cache.7z
rm -f the-archdruid-report.zip
7z u web_cache.7z web_cache
zip -r the-archdruid-report.zip the-archdruid-report
