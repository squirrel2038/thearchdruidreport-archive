#!/bin/sh
set -e

ARCHIVES="thearchdruidreport-archive.tar.xz web_cache.tar.xz"

for name in $ARCHIVES; do
    rm -f $name
    rm -f $name.list
done

./generate_posts_json.py
./populate_web_cache.py
./generate_pages.py

find thearchdruidreport-archive -type f | sort > thearchdruidreport-archive.tar.xz.list
./list_web_cache_files.py web_cache > web_cache.tar.xz.list

for name in $ARCHIVES
    # The tar on macOS doesn't support -a, so specify -J for xz.
    XZ_OPT='-v9' tar cfJ $name -T $name.list
done

shasum -a256 $ARCHIVES > SHA256SUMS
