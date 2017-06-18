#!/usr/bin/env python3
from datetime import datetime, timedelta
import requests
import sys
import time
import os

import util
import web_cache


def _http_date_str(dtobj):
    # The obvious approach is to use datetime.strftime, but AFAICT, that's
    # incorrect, because strftime uses the current locale for the names of week
    # days and months, but HTTP uses English.
    assert dtobj.tzinfo is None
    weekday = [
        "Mon", "Tue", "Wed", "Thu",
        "Fri", "Sat", "Sun",
    ][dtobj.weekday()]
    mon = [
        "Jan", "Feb", "Mar",
        "Apr", "May", "Jun",
        "Jul", "Aug", "Sep",
        "Oct", "Nov", "Dec",
    ][dtobj.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
        weekday, dtobj.day, mon, dtobj.year,
        dtobj.hour, dtobj.minute, dtobj.second
    )


def _enum_cache_entries(cache_dir):
    for d, _, files in os.walk(cache_dir):
        for f in files:
            if f.endswith(".data"):
                p = os.path.join(d, f[:-5])
                assert os.path.exists(p + ".url")
                assert os.path.exists(p + ".timestamp")
                assert not os.path.exists(p + ".fail")
                yield p


# XXX: This experiment didn't work.  On both the main Blogger site and on the
# Blogspot image servers, the server only returns 304 if the If-Modified-Since
# setting is no more than a day or so old.  Since refreshing the cache
# effectively requires redownloading everything anyway, deleting the web_cache
# is the easy to do that.


for entry in sorted(_enum_cache_entries("web_cache")):
    stamp = web_cache.read_timestamp_file(entry + ".timestamp")
    stamp -= timedelta(days=2)
    url = util.get_file_text(entry + ".url")
    print(url)
    #break
    print(_http_date_str(stamp))
    r = requests.get(url, timeout=60.0, headers={"If-Modified-Since": _http_date_str(stamp)})
    print(r)

    if r.status_code == 200:
        old_data = util.get_file_data(entry + ".data")
        new_data = r.content
        print(old_data == new_data)


    time.sleep(0.2)
