#!/bin/sh
set -e
cd "$(dirname "$0")"

rm -fr dist
mkdir -p dist

SUFFIX=
if [ "$RELNAME" != "" ]; then
    SUFFIX=-${RELNAME}
fi

ARCHIVES=
ARCHIVES="$ARCHIVES thearchdruidreport-archive$SUFFIX.tar.xz"
ARCHIVES="$ARCHIVES web_cache$SUFFIX.tar.xz"

./generate_posts_json.py
./populate_web_cache.py
./generate_pages.py

find thearchdruidreport-archive -type f | sort > dist/thearchdruidreport-archive$SUFFIX.tar.xz.list
./list_web_cache_files.py web_cache            > dist/web_cache$SUFFIX.tar.xz.list

for name in $ARCHIVES; do
    # The tar on macOS doesn't support -a, so specify -J for xz.
    XZ_OPT='-v9' tar cfJ dist/$name -T dist/$name.list
    rm -f dist/$name.list
done

(cd dist && shasum -a256 $ARCHIVES) > dist/SHA256SUMS
