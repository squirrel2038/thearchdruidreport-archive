#!/usr/bin/env python3
from datetime import datetime
import hashlib
import re
import os
import requests
import sys
import time
import threading

import util
import parallel_locking

WEB_CACHE_DIR = os.path.dirname(__file__) + "/web_cache"
POST_REQUEST_SLEEP_TIME = 2.0
_lock = parallel_locking.make_lock("web_cache")


_scheme_re = re.compile(r"^(?:file|http|https):")
_bad_url_re = re.compile(r"[^a-z0-9\~\-\`\!\@\#\$\%\&\(\)\_\+\=\{\}\[\]\;\,\.]+")
def _canonbase(url):
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

    ret = os.path.join(WEB_CACHE_DIR, url, hashstr)
    ret = util.abspath(ret)
    return ret


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


def has(url):
    assert _lock
    with _lock:
        return os.path.exists(_canonbase(canonurl(url)) + ".url")

class ResourceNotAvailable(Exception):
    def __init__(self, reason):
        self.reason = reason


def get(url):
    assert _lock
    with _lock:
        url = canonurl(url)
        path = _canonbase(url)

        if not os.path.exists(path + ".url") or not (os.path.exists(path + ".data") or os.path.exists(path + ".fail")):
            print("requesting", url)
            sys.stdout.flush()
            try:
                r = requests.get(url)
                if r.status_code not in [200, 403, 404, 410, 500, 504]:
                    raise RuntimeError("ERROR: bad status code: " + str(r.status_code))
                if r.status_code == 200:
                    util.set_file_data(path + ".data", r.content)
                else:
                    print("WARNING: %d error downloading URL: %s" % (r.status_code, url))
                    sys.stdout.flush()
                    util.set_file_text(path + ".fail", str(r.status_code) + "\n")
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as err:
                print("WARNING: Connection error downloading URL: %s\n  %s" % (url, repr(err)))
                sys.stdout.flush()
                util.set_file_text(path + ".fail", repr(err) + "\n")
            util.set_file_text(path + ".timestamp", datetime.now().isoformat())
            util.set_file_text(path + ".url", url)
            time.sleep(POST_REQUEST_SLEEP_TIME)

        assert util.get_file_text(path + ".url") == url
        has_data = os.path.exists(path + ".data")
        has_fail = os.path.exists(path + ".fail")
        if has_data and has_fail:
            raise RuntimeError("ERROR: Both %(path)s.data and %(path)s.fail exist" % {"path": path})
        if has_data:
            with open(path + ".data", "rb") as fp:
                return fp.read()
        if has_fail:
            raise ResourceNotAvailable(util.get_file_text(path + ".fail"))
        raise RuntimeError("ERROR: internal error on URL " + url)


if __name__ == "__main__":
    # for testing
    get("https://thearchdruidreport.blogspot.com/2013/01/into-unknown-country.html")
