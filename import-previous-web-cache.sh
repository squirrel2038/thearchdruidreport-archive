#!/bin/sh
set -e

rm -fr web_cache
rm -fr web_cache_feed_avatars
rm -fr web_cache_import
mkdir -p web_cache_import
for x in "$@"; do
    tar xf "$x" --strip-components=1 -C web_cache_import
done

./refresh-web-cache.sh web_cache_import
