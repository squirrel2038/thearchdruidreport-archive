#!/bin/sh
#
# Command:
#
#    (time ADR_RELNAME=CPnnn ADR_RETRY=1 ./make-archive.sh) >& LOG
#

set -e
cd "$(dirname "$0")"

rm -fr dist
mkdir -p dist

ADR_SUFFIX=
if [ "$ADR_RELNAME" != "" ]; then
    ADR_SUFFIX=-${ADR_RELNAME}
fi

ARCHIVES=
ARCHIVES="$ARCHIVES thearchdruidreport-archive$ADR_SUFFIX.tar.xz"
ARCHIVES="$ARCHIVES web_cache$ADR_SUFFIX.tar.xz"

./generate_posts_json.py
./download_feed_avatars.py list
./populate_web_cache.py
./generate_pages.py

if [ "$ADR_RETRY" != "" ]; then
    # Retry each failed web request a second time.
    echo "Removing web failed requests and regenerating..."
    ./remove-web-cache-failures.sh
    ./populate_web_cache.py
    ./generate_pages.py
fi

find thearchdruidreport-archive -type f | sort > dist/thearchdruidreport-archive$ADR_SUFFIX.tar.xz.list
./list_web_cache_files.py web_cache            > dist/web_cache$ADR_SUFFIX.tar.xz.list

for name in $ARCHIVES; do
    # The tar on macOS doesn't support -a, so specify -J for xz.
    XZ_OPT='-v9' tar cfJ dist/$name -T dist/$name.list
    rm -f dist/$name.list
done

(cd dist && shasum -a256 $ARCHIVES) > dist/SHA256SUMS
