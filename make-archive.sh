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

if [ "$ADR_RETRY" != "" ]; then
    # Retry each failed web request on the first run.  If requests were copied
    # from a previous run, doing the extra requests isn't too expensive.
    echo "Removing failed web requests..."
    [ -e web_cache ] && ./remove-web-cache-failures.sh web_cache
fi

./generate_posts_json.py
./download_feed_avatars.py list
./populate_web_cache.py
./download_feed_avatars.py fetch
./generate_pages.py
./generate_blogger_export_xml.py
./consolidate_json.py
./survey-avatars.py
cp blogger_export.xml        dist/blogger_export${ADR_SUFFIX}.xml
cp blogger_export_sample.xml dist/blogger_export_sample${ADR_SUFFIX}.xml
cp blog.json                 dist/blog${ADR_SUFFIX}.json

if [ "$ADR_RETRY" != "" ]; then
    # Retry each failed web request a second time.
    echo "Removing failed web requests and regenerating..."
    ./remove-web-cache-failures.sh web_cache
    ./populate_web_cache.py
    ./download_feed_avatars.py fetch
    ./generate_pages.py
fi

find thearchdruidreport-archive -type f | sort > dist/thearchdruidreport-archive$ADR_SUFFIX.tar.xz.list
./list_web_cache_files.py web_cache            > dist/web_cache$ADR_SUFFIX.tar.xz.list

for name in $ARCHIVES; do
    # The tar on macOS doesn't support -a, so specify -J for xz.
    XZ_OPT='-v9' tar cfJ dist/$name -T dist/$name.list
    rm -f dist/$name.list
done

# Bundle up these extra things.
tar cfJ dist/img_cache$ADR_SUFFIX.tar.xz img_cache

(cd dist && shasum -a256 *.tar.xz) > dist/SHA256SUMS
