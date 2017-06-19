#!/bin/bash
#
# Refresh posts and comments in the web_cache by deleting them.
#

if [ "$1" == "" ]; then
    echo error: Usage: $0 cache_dir
    exit 1
fi

rm -fr $1/www.blogger.com/comment.*
rm -fr $1/thearchdruidreport.blogspot.com
