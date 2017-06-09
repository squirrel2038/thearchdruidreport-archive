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

web_cache_DIR = os.path.dirname(__file__) + "/web_cache"
POST_REQUEST_SLEEP_TIME = 2.0
_lock = threading.Lock() # Replace this default to do multiprocessing.


def set_lock(lock):
    global _lock
    _lock = lock


# Use \\?\C:\path\file syntax to: (a) avoid path length limits and (b) avoid device files.
def _fixup_win32_path(path):
    path = os.path.abspath(path)
    if re.match(r"[a-zA-Z]:\\", path[0:3]):
        return "\\\\?\\" + path[0].upper() + path[1:]
    elif re.match(r"\\\\[^\\]+\\"):
        return "\\\\UNC\\" + path[2:]
    else:
        raise RuntimeError("ERROR: unrecognized Windows path: " + path)


_scheme_re = re.compile(r"^(?:file|http|https):")
_bad_url_re = re.compile(r"[^a-z0-9\~\-\`\!\@\#\$\%\&\(\)\_\+\=\{\}\[\]\;\'\,\.]+")
def _canonbase(url):
    # Record the hash for the original unsanitized URL.
    hashstr = hashlib.sha256(url.encode("utf8")).hexdigest()[0:40]

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

    ret = os.path.join(web_cache_DIR, url, hashstr)
    if sys.platform == "win32":
        ret = _fixup_win32_path(ret)
    return ret


def _canonurl(url):
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
    with _lock:
        return os.path.exists(_canonbase(_canonurl(url)) + ".url")

class ResourceNotAvailable(Exception):
    pass


def get(url):
    with _lock:
        url = _canonurl(url)
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
            raise ResourceNotAvailable()
        raise RuntimeError("ERROR: internal error on URL " + url)


if __name__ == "__main__":
    # for testing
    get("https://thearchdruidreport.blogspot.com/2013/01/into-unknown-country.html")
