#!/usr/bin/env python3
from datetime import datetime, timedelta
import hashlib
import re
import os
import requests
import sys
import time
import threading

import util
import parallel_locking

NO_ENTRY = 0
ENTRY_VALID = 1
ENTRY_INVALID = 2

_cache_dir = os.path.dirname(__file__) + "/web_cache"
_cache_dir_under = os.path.dirname(__file__) + "/web_cache_import"
POST_REQUEST_SLEEP_TIME = 2.0
_lock = parallel_locking.make_lock("web_cache")



_scheme_re = re.compile(r"^(?:file|http|https):")
_bad_url_re = re.compile(r"[^a-z0-9\~\-\`\!\@\#\$\%\&\(\)\_\+\=\{\}\[\]\;\,\.]+")
def _canonbase(cache_dir, url):
    # Record the hash for the original unsanitized URL.
    hashstr = urlhash(url)

    # Sanitization the URL to a filename that still preserves some of the URL's structure.
    url = url.lower()
    url = _scheme_re.sub("", url)

    # Sanitize each path component separately.
    parts = []
    for part in url.split("/"):
        part = "-".join(_bad_url_re.sub(" ", part).split())
        part = part[0:120]
        part = ".".join(part.replace(".", " ").split())
        if len(part) != 0:
            parts.append(part)
    url = "/".join(parts)

    # Cap the path length.
    url = url[0:500]
    url = ".".join(url.replace(".", " ").split())

    ret = os.path.join(cache_dir, url, hashstr)
    ret = util.abspath(ret)
    return ret


def set_cache_dir(path, under_path=None):
    # Use `path` as the cache directory.  If `under_path` is non-None, then
    # files will be copied from it to the primary cache directory when they're
    # requested.
    global _cache_dir
    global _cache_dir_under
    _cache_dir = path
    _cache_dir_under = under_path


def urlhash(url):
    return hashlib.sha256(canonurl(url).encode("utf8")).hexdigest()[0:40]


def canonurl(url):
    if url.startswith("//"):
        return "https:" + url
    elif url.lower().startswith("http://"):
        return url
    elif url.lower().startswith("https://"):
        return url
    else:
        # In particular, we need to detect file: and disallow it.
        raise RuntimeError("ERROR: invalid URL scheme: " + url)


class ResourceNotAvailable(Exception):
    def __init__(self, reason):
        self.reason = reason


def _entry_state(cache_dir, url):
    # Determine the state of the URL in the specified cache directory.
    path = _canonbase(cache_dir, url)
    has_url = os.path.exists(path + ".url")
    has_data = os.path.exists(path + ".data")
    has_fail = os.path.exists(path + ".fail")
    if has_data and has_fail:
        raise RuntimeError("ERROR: Both %(path)s.data and %(path)s.fail exist" % {"path": path})
    if has_url:
        assert util.get_file_text(path + ".url") == url
        if has_data:
            return ENTRY_VALID
        if has_fail:
            return ENTRY_INVALID
    return NO_ENTRY


def parse_timestamp_str(stamp):
    # In early versions of the archive, the timestamps were implicitly in the
    # CDT -05:00 timezone.  We want to instead return a naive datetime in UTC.
    if stamp.endswith("Z"):
        ret = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        ret = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S.%f")
        ret += timedelta(hours=5)
    return ret


def timestamp_str(dtobj):
    # Use native datetime objects in UTC.
    assert dtobj.tzinfo is None
    ret = dtobj.isoformat() + "Z"
    assert parse_timestamp_str(ret) == dtobj # Make sure the string is valid.
    return ret


def read_timestamp_file(path):
    return parse_timestamp_str(util.get_file_text(path).rstrip())

def write_timestamp_file(path, stamp):
    util.set_file_text(path, timestamp_str(stamp) + "\n")


def get(url):
    assert _lock
    with _lock:
        url = canonurl(url)
        path = _canonbase(_cache_dir, url)

        if _entry_state(_cache_dir, url) == NO_ENTRY:
            under_state = NO_ENTRY
            if _cache_dir_under is not None:
                under_state = _entry_state(_cache_dir_under, url)
                if under_state != NO_ENTRY:
                    under_path = _canonbase(_cache_dir_under, url)
                    print("copying request from %s: %s" % (_cache_dir_under, url))
                    if under_state == ENTRY_VALID:
                        util.set_file_data(path + ".data",      util.get_file_data(under_path + ".data"))
                    elif under_state == ENTRY_INVALID:
                        util.set_file_text(path + ".fail",      util.get_file_text(under_path + ".fail"))
                    else:
                        raise RuntimeError("ERROR: internal error on URL " + url + ": invalid under_state")
                    write_timestamp_file(path + ".timestamp", read_timestamp_file(under_path + ".timestamp"))
                    util.set_file_text(path + ".url",           util.get_file_text(under_path + ".url"))

            if under_state == NO_ENTRY:
                print("requesting", url)
                sys.stdout.flush()
                try:
                    r = requests.get(url, timeout=60.0)
                    if r.status_code not in [200, 403, 404, 410, 429, 500, 503, 504]:
                        raise RuntimeError("ERROR: bad status code: " + str(r.status_code))
                    if r.status_code == 200:
                        util.set_file_data(path + ".data", r.content)
                    else:
                        print("WARNING: %d error downloading URL: %s" % (r.status_code, url))
                        sys.stdout.flush()
                        util.set_file_text(path + ".fail", str(r.status_code) + "\n")
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as err:
                    print("WARNING: Connection error downloading URL: %s\n  %s" % (url, repr(err)))
                    sys.stdout.flush()
                    util.set_file_text(path + ".fail", repr(err) + "\n")
                write_timestamp_file(path + ".timestamp", datetime.utcnow())
                util.set_file_text(path + ".url", url)
                time.sleep(POST_REQUEST_SLEEP_TIME)

        state = _entry_state(_cache_dir, url)
        if state == ENTRY_VALID:
            return util.get_file_data(path + ".data")
        elif state == ENTRY_INVALID:
            raise ResourceNotAvailable(util.get_file_text(path + ".fail"))
        else:
            raise RuntimeError("ERROR: internal error on URL " + url + ": invalid state")


if __name__ == "__main__":
    # for testing
    get("https://thearchdruidreport.blogspot.com/2013/01/into-unknown-country.html")
