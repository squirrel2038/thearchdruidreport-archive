#!/bin/bash
# Remove web_cache requests that have failed so they will be retried.
find $1 -name '*.fail' -print0 | while read -d '' -r var; do
    rm -f "${var%.fail}.fail"
    rm -f "${var%.fail}.url"
    rm -f "${var%.fail}.data"
    rm -f "${var%.fail}.timestamp"
done
