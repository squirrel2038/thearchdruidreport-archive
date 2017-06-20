#!/usr/bin/env python3
#
# Verify that the downloaded HTML posts and the JSON feed posts have the
# same images in them, and verify that the images derived from the JSON are
# in the web_cache.
#

from bs4 import BeautifulSoup
import json
import re

import parallel
import util
import web_cache


BLOG_JSON = json.loads(util.get_file_text("blog.json"))


def _noschema(url):
    return re.sub(r"^https?:", "", url)


def _parent_image(img):
    # If we have an image hyperlink to what appears to be an image itself,
    # hosted on Blogspot, then it's likely an expandable image in the main
    # post body, and it'd make sense to archive it.
    if img.parent.name == "a" and "href" in img.parent.attrs:
        href = img.parent.attrs["href"]
        if re.match(r"(https?:)?//[1234]\.bp\.blogspot\.com/.*\.(png|gif|jpg|jpeg)$", href, re.IGNORECASE):
            return href
    return None


def _check_post_image(jurl, hurl):
    assert hurl.startswith("//") or hurl.startswith("https://")
    assert jurl.startswith("http://") or jurl.startswith("https://")
    assert _noschema(jurl) == _noschema(hurl)
    http_bytes = web_cache.get("http:" + _noschema(jurl))
    https_bytes = web_cache.get("https:" + _noschema(jurl))
    if http_bytes != https_bytes:
        print("WARNING: http and https schemes differ: %s" % _noschema(jurl))


def _check_post(post_index):
    post = BLOG_JSON[post_index]

    jbody = post["content"]
    if "<img" not in jbody:
        # This post has no images -- skip the expensive HTML parsing.
        return

    print("Checking %s ..." % post["url"])

    jbody = BeautifulSoup(jbody, "lxml")
    hbody = BeautifulSoup(web_cache.get(post["url"]), "lxml")
    hbody = hbody.select_one(".post-body")

    jimg = jbody.find_all("img")
    himg = hbody.find_all("img")

    assert len(jimg) == len(himg)
    for j, h in zip(jimg, himg):
        _check_post_image(j.attrs["src"], h.attrs["src"])
        jparent = _parent_image(j)
        hparent = _parent_image(h)
        assert (jparent is None) == (hparent is None)
        if jparent is not None:
            _check_post_image(jparent, hparent)


def _main(apply_, flush):
    for i in range(len(BLOG_JSON)):
        apply_(_check_post, (i,))
        #_check_post(i)


if __name__ == "__main__":
    parallel.run_main(_main)
