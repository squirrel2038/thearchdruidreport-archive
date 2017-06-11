#!/usr/bin/env python3
#
# Install these pip packages:
#  - pip3 install beautifulsoup4
#  - pip3 install lxml
#  - pip3 install requests
#

from bs4 import BeautifulSoup, Comment
from copy import copy
import PIL.Image
import io
import hashlib
import html
import json
import multiprocessing
import multiprocessing.managers
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import image_compressor

import web_cache
import util

_page_cache = {}
_pil_image_cache = {}
_intern_image_cache = {}
_fs_lock = None
_image_compressor = None

OUTPUT_DIRECTORY = "the-archdruid-report"

IMAGE_TYPE_NORMAL = "normal"
IMAGE_TYPE_RESOURCE = "resource"
IMAGE_TYPE_AVATAR = "avatar"

def _page(url):
    global _page_cache
    if url not in _page_cache:
        _page_cache[url] = BeautifulSoup(web_cache.get(url), "lxml")
    return _page_cache[url]

def _pil_image(url):
    global _pil_image_cache
    if url not in _pil_image_cache:
        _pil_image_cache[url] = PIL.Image.open(io.BytesIO(web_cache.get(url)))
    return _pil_image_cache[url]

def _soup(text, tag):
    ret = BeautifulSoup(text, "lxml")
    if tag is not None:
        ret = getattr(ret, tag)
    return ret

def _get_comments_count(url):
    main_doc = _page(url)
    m = re.match(r"^(\d+) comments?:$", main_doc.select_one(".comments").h4.string)
    return int(m.group(1))

def _get_comments(url):
    total_count = _get_comments_count(url)
    page_count = (total_count + 199) // 200
    ret = []

    for page in range(1, page_count + 1):
        page_url = url if page == 1 else url + ("?commentPage=%d" % page)
        page_comments = copy(_page(page_url).select_one("#comments-block"))

        # remove "Delete Comment" buttons
        for x in page_comments.select(".blog-admin"):
            x.decompose()

        for i, x in enumerate(page_comments.contents):
            if i % 2 == 0:
                assert x.name is None
                assert str(x) == "\n"
            else:
                assert x.name == {0:"dt", 1:"dd", 2:"dd"}[(i - 1) / 2 % 3]
        ret += [Comment("comments from %s" % page_url)]
        ret += page_comments.contents

    return total_count, ret

def _replace_delay_load(doc):
    # Most comment avatar images are "delayLoad". (Special Javascript I guess?)
    for x in doc.select(".delayLoad"):
        # Delayload img.
        assert x.name == "img"
        assert x.attrs["class"] == ["delayLoad"]
        assert x.attrs["style"] == "display: none;"
        assert "longdesc" in x.attrs
        # Followed by a noscript tag.
        n = x.next_sibling
        if n.name is None:
            n = n.next_sibling
        assert n.name == "noscript"
        assert len(n.contents) == 1
        nn = n.contents[0]
        assert nn.name == "img"
        assert nn.attrs["src"] == x.attrs["longdesc"]
        # Nuke the delayLoad image and replace it with the noscript img.
        nn = nn.extract()
        n.decompose()
        x.replace_with(nn)

def parse_tar_url(url):
    m = re.match(r"^https://thearchdruidreport.blogspot.com/(20\d\d)/(\d\d)/(.+[.]html)$", url)
    year = int(m.group(1))
    month = int(m.group(2))
    page = m.group(3)
    return year, month, page

class Post:
    def __init__(self):
        pass

def load_posts():
    ret = []
    posts_json = json.loads(util.get_file_text("posts.json"))
    for post in posts_json:
        e = Post()
        e.title = post["title"]
        e.url = post["url"]
        e.year, e.month, e.page = parse_tar_url(e.url)
        e.relurl = "%04d/%02d/%s" % (e.year, e.month, e.page)
        ret.append(e)
    return ret

def _month_name(no):
    return [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ][no - 1]


def _gen_blog_archive(url_to_root, cur_year, cur_month):
    ret = _soup('<div id="BlogArchive1_ArchiveList"></div>', "div")
    all_posts = load_posts()
    years = {}
    months = {}
    cur_year = int(cur_year)
    cur_month = int(cur_month)

    for year in sorted(set([x.year for x in all_posts]))[::-1]:
        is_open = year == cur_year
        e = """
            <ul class="hierarchy">
                <li class="archivedate %(class)s" id="arc_%(id)s">
                    <a class="toggle" onclick="arc_tog('%(id)s')" href="javascript:void(0)">
                        <span class="zippy%(zippyclass)s">%(spantext)s&nbsp;</span>
                    </a>
                    <a class="post-count-link" href="%(url_to_root)s/%(year)04d/%(last_month)02d/index.html">%(year)04d</a> (%(count)d)</li>
            </ul>
            """ % {
                "class": ["collapsed", "expanded"][is_open],
                "zippyclass": ["", " toggle-open"][is_open],
                "spantext": ["►", "▼"][is_open],
                "id": "%04d" % year,
                "url_to_root": url_to_root,
                "year": year,
                "last_month": max([x.month for x in all_posts if x.year == year]),
                "count": len([x for x in all_posts if x.year == year]),
            }
        e = _soup(e, "ul")
        ret.append(e)
        years[year] = e.li

    del year

    for month in sorted(set([x.month for x in all_posts if x.year == cur_year]))[::-1]:
        is_open = month == cur_month
        e = """
            <ul class="hierarchy">
                <li class="archivedate %(class)s" id="arc_%(id)s">
                    <a class="toggle" onclick="arc_tog('%(id)s')" href="javascript:void(0)">
                        <span class="zippy%(zippyclass)s">%(spantext)s&nbsp;</span>
                    </a>
                    <a class="post-count-link" href="%(url_to_root)s/%(year)04d/%(month)02d/index.html">%(month_name)s</a> (%(count)d)<ul class="posts"></ul>
                </li>
            </ul>
        """ % {
            "class": ["collapsed", "expanded"][is_open],
            "zippyclass": ["", " toggle-open"][is_open],
            "spantext": ["►", "▼"][is_open],
            "id": "%04d_%02d" % (cur_year, month),
            "url_to_root": url_to_root,
            "year": cur_year,
            "month": month,
            "month_name": _month_name(month),
            "count": len([x for x in all_posts if (x.year, x.month) == (cur_year, month)]),
        }
        e = _soup(e, "ul")
        years[cur_year].append(e)
        months[(cur_year, month)] = e.select_one(".posts")

    for p in [x for x in all_posts if (x.year, x.month) == (cur_year, cur_month)]:
        parent = months[(p.year, p.month)]
        parent.append(_soup('<li><a href="%s/%s">%s</a></li>' % (url_to_root, p.relurl, html.escape(p.title, False)), "li"))

    return ret


def _count_string(n, thing):
    return "%d %s%s" % (n, thing, ("" if n == 1 else "s"))


MAIN_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
    <link href="%(resources)s/favicon.ico" rel="icon" type="image/x-icon"/>
    <link type="text/css" rel="stylesheet" href="%(resources)s/58827200-widget_css_bundle.css"/>
    <link type="text/css" rel="stylesheet" href="%(resources)s/blogger-page-skin-1.css"/>
    <link type="text/css" rel="stylesheet" href="%(resources)s/blogger-authorization.css"/>
    <title></title>

    <script src="%(resources)s/posts.js"></script>
    <script src="%(resources)s/archive_toggle.js"></script>
</head>
<body>
    <div id="outer-wrapper">
        <div id="header-wrapper">
            <div class="header section" id="header">
                <div class="widget Header" data-version="1" id="Header1">
                    <div id="header-inner">
                        <div class="titlewrapper">
                            <h1 class="title">
                                <a href="https://thearchdruidreport.blogspot.com/">The Archdruid Report</a>
                            </h1>
                        </div>
                        <div class="descriptionwrapper">
                            <p class="description"><span>Druid perspectives on nature, culture, and the future of industrial society</span></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="crosscol-wrapper" style="text-align:center">
            <div class="crosscol no-items section" id="crosscol"></div>
        </div>

        <div id="main-wrap1">
            <div id="main-wrap2">
                <div class="main section" id="main">
                    <div class="widget Blog" data-version="1" id="Blog1">
                        <div class="blog-posts hfeed"><!-- POSTS INSERTED INTO THIS TAG --></div>
                        <div class="blog-pager"><!-- TAG IS REPLACED --></div>

                        <!-- Keep this here so the borders on the left/right don't have a gap. -->
                        <div class="post-feeds"><div class="feed-links">&nbsp;</div></div>

                    </div>
                </div>
            </div>
        </div>

        <div id="sidebar-wrap">
            <div id="sidebarbottom-wrap1"><!-- TAG IS REPLACED --></div>
        </div>

        <div id="footer-wrap1">
            <div id="footer-wrap2">
                <div class="footer no-items section" id="footer"></div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def _set_promo_img_size(img):
    w, h = _pil_image(img.attrs["src"]).size
    if w > 214:
        h = round(h * 214 / w)
        w = 214
    img.attrs["width"] = str(w)
    img.attrs["height"] = str(h)


def _gen_sidebar(page_url, url_to_root):
    # Replace the sidebar with the one from the source document.
    src = _page(page_url)

    ret = copy(src.select_one('#sidebarbottom-wrap1'))

    # Fixup the images in the sidebar -- downscale them to 214px wide
    for x in ret.select("div.widget.Image"):
        _set_promo_img_size(x.img)

    # Remove cruft (e.g. admin stuff) from sidebar widgets (e.g. promo images)
    # (We have to separate the classes here, but we didn't have to elsewhere.  I have no idea why.)
    for x in ret.select(".widget-item-control"):
        x.decompose()
    for x in ret.select(".clear"):
        x.decompose()

    # Fixup the blog archive
    year, month, _ = parse_tar_url(page_url)
    ret.select_one("#BlogArchive1_ArchiveList").replace_with(_gen_blog_archive(url_to_root, year, month))

    return ret


# parent is the #comments-block <dl> tag that contains, for each comment,
# three tags:
#   <dt class="comment-author" ... />
#   <dd class="comment-body" ... />
#   <dd class="comment-footer" ... />
# It also contains one <!-- --> comment for each original HTML page of comments.
def _compress_comments_html(parent):
    _replace_delay_load(parent)
    for e in parent.find_all("a", class_="avatar-hovercard"):
        # Clean useless stuff off the avatar anchor.
        assert e.attrs["id"].startswith("av-")
        assert e.attrs["onclick"] == ""
        del e.attrs["onclick"]
        del e.attrs["id"]
        # Optimize the avatar image.
        i = e.contents[0]
        assert i.name == "img"
        assert i.attrs["alt"] == ""
        del i.attrs["alt"]
    for e in parent.find_all("dd", class_="comment-body"):
        assert e.attrs["id"].startswith("Blog1_cmt-")
        del e.attrs["id"]
    for e in parent.select("span.comment-timestamp > a"):
        assert e.attrs["title"] == "comment permalink"
        m = re.match(r".*(#c\d+)$", str(e.attrs["href"]))
        assert m
        e.attrs["href"] = m.group(1)


def _gen_blog_post(page_url, include_comments, should_add_hyperlinks):
    doc = _page(page_url)
    date_outer = _soup("""
            <div class="date-outer">
                <h2 class="date-header"><!-- TAG IS REPLACED --></h2>
                <div class="date-posts">
                    <div class="post-outer">
                        <div class="post"><!-- TAG IS REPLACED --></div>
                        <div class="comments"><!-- TAG IS REPLACED --></div>
                    </div>
                </div>
            </div>""",
        "div")
    date_outer.select_one(".date-header").replace_with(copy(doc.select_one('.date-header')))
    date_outer.select_one(".post").replace_with(copy(doc.select_one('.post')))
    footer = date_outer.select_one(".post-footer")
    for x in footer.select(".reaction-buttons, .post-comment-link, .post-icons, .post-share-buttons, .post-footer-line-2, .post-footer-line-3"):
        x.decompose()

    if should_add_hyperlinks:
        # Title hyperlink
        title_element = date_outer.select_one(".post-title")
        anchor = _soup("""<a href="%s"></a>""" % page_url, "a")
        for x in reversed(title_element.contents):
            anchor.insert(0, x)
        title_element.append(anchor)
        # Comments hyperlink
        footer.select_one(".post-footer-line-1").append(_soup("""
                <span class="post-comment-link">
                    <a class="comment-link" href="%(url)s#comments">%(comments)s:</a>
                </span>
                """ % {
                    "url": page_url,
                    "comments": _count_string(_get_comments_count(page_url), "comment")
                },
            "span"))

    # Add comments.
    if include_comments:
        total_comments, comment_elements = _get_comments(page_url)
        comments_div = _soup("""
                <div class="comments" id="comments">
                    <a name="comments"></a>
                    <h4>%(comments)s:</h4>
                    <div id="Blog1_comments-block-wrapper">
                        <dl class="avatar-comment-indent" id="comments-block">
                        </dl>
                    </div>
                </div>""" % {"comments" : _count_string(total_comments, "comment")},
            "div")
        comments_div_dl = comments_div.select_one("#comments-block")
        for e in comment_elements:
            comments_div_dl.append(e)
        date_outer.select_one(".comments").replace_with(comments_div)
        _compress_comments_html(comments_div_dl)
    else:
        date_outer.select_one(".comments").decompose()

    # Attach the post ID to the post element.  Ordinarily, it's on an
    # "<a name>", but those are marked obsolete now, so best not to use them?
    post_id = str(date_outer.find("meta", itemprop="postId").attrs["content"])
    post_el = date_outer.select_one(".post")
    assert "id" not in post_el.attrs
    post_el.attrs["id"] = post_id

    return date_outer


def _write_page(doc, path):
    util.set_file_text(path, str(doc))


_friendly_image_name_re = re.compile(r"[^a-z0-9]+")
def _friendly_image_name(url):
    # We get crazy URLs like these:
    #   https://4.bp.blogspot.com/-oMGCzPx1G5g/Td8IWS29goI/AAAAAAAAABE/wuSDgLAHghA/s35/portrait%25252Bof%25252Bshannon%25252Bcopy.jpg
    # Turn it into:
    #   portrait-of-shannon-copy
    if "#" in url:
        url = url[:url.index("#")]
    if "?" in url:
        url = url[:url.index("?")]
    for i in range(3):
        url = urllib.request.unquote(url).replace("+", " ")
    url = os.path.basename(url)
    url = url.strip()
    url = url.lower() # Avoid case-sensitivity problems on Win/OSX.
    for ext in [".png", ".gif", ".jpg", ".jpeg", ".svg"]:
        if url.endswith(ext):
            url = url[:-len(ext)]
            break
    url = _friendly_image_name_re.sub(" ", url)
    url = " ".join(url.split())
    url = url[:30]
    url = "-".join(url.split())
    if url == "":
        url = "img"
    return url


def _intern_image_async(url, image_type=IMAGE_TYPE_NORMAL, html_size=None, hidpi=False):
    global _intern_image_cache

    memo_key = (url, image_type, html_size, hidpi)
    if memo_key in _intern_image_cache:
        return AsyncImageResultCached(*_intern_image_cache[memo_key])

    if html_size is None or html_size == (None, None):
        html_size = None
    else:
        # XXX: If only one dimension is provided, this will fail, and we'll
        # need to do implement something sensible here.
        html_size = (int(html_size[0]), int(html_size[1]))

    if url == "":
        # This happens with the avatar icon on comment:
        # https://thearchdruidreport.blogspot.com/2015/03/peak-meaninglessness.html?showComment=1425652426980#c1700234895902505359
        print("WARNING: Skipping img with src=''")
        return None

    try:
        img_bytes = web_cache.get(url)
    except web_cache.ResourceNotAvailable:
        return None

    extension = util.image_extension(img_bytes)
    if extension is None:
        return None

    name = hashlib.sha256(img_bytes).hexdigest()[:6]
    if image_type != IMAGE_TYPE_AVATAR:
        name = _friendly_image_name(url) + "-" + name
    base_dir = "img"
    if image_type == IMAGE_TYPE_AVATAR:
        base_dir = "avt"

    if extension == ".svg":
        if hidpi:
            return None
        # Short-circuit the image compressor for SVG images.
        return AsyncImageResultCached(_write_image_file(base_dir, name, extension, img_bytes), None)

    # If hidpi is true, then abort if there aren't enough pixels to justify
    # a high-DPI resampling.
    resample_size = None
    hidpi_ratio = None
    img = _pil_image(url)
    if html_size is None:
        if hidpi:
            return None
        html_size = img.size
    else:
        if not hidpi:
            if any(img.size[d] > html_size[d] for d in (0, 1)):
                resample_size = tuple(min(img.size[d], html_size[d]) for d in (0, 1))
        else:
            hidpi_ratio = min(2.0, min(img.size[d] / html_size[d] for d in (0, 1)))
            if hidpi_ratio >= 1.5:
                resample_size = tuple(round(html_size[d] * hidpi_ratio) for d in (0, 1))
            else:
                return None

    guetzli_quality = 95
    if img.mode in ["L", "LA", "RGBA"] or "transparency" in img.info:
        guetzli_quality = 0
    job = (name, url, resample_size, guetzli_quality)
    is_job_cached = _image_compressor.has_cached(job)
    _image_compressor.start_compress_async(job)

    ret = AsyncImageResult(base_dir, name, hidpi_ratio, job, memo_key)
    if is_job_cached:
        # Call this prematurely to force the final path into our
        # process' cache.  Performance hack.
        ret.get()
    return ret


class AsyncImageResult:
    def __init__(self, base_dir, name, hidpi_ratio, job, memo_key):
        self._base_dir = base_dir
        self._name = name
        self._hidpi_ratio = hidpi_ratio
        self._job = job
        self._memo_key = memo_key

    def get(self):
        global _intern_image_cache
        cache_path, name_extra = _image_compressor.compress(self._job)
        img_bytes = util.get_file_data(cache_path)
        html_path = _write_image_file(self._base_dir, self._name + name_extra,
                                      os.path.splitext(cache_path)[1], img_bytes)
        _intern_image_cache[self._memo_key] = (html_path, self._hidpi_ratio)
        return html_path

    def hidpi_ratio(self):
        return self._hidpi_ratio


class AsyncImageResultCached:
    def __init__(self, result, hidpi_ratio):
        self._result = result
        self._hidpi_ratio = hidpi_ratio

    def get(self):
        return self._result

    def hidpi_ratio(self):
        return self._hidpi_ratio


def _intern_image(url, *args, **kwargs):
    ret = _intern_image_async(url, *args, **kwargs)
    return None if ret is None else ret.get()


def _write_image_file(base_dir, name, extension, data):
    with _fs_lock:
        extra_cnt = 1
        extra_txt = ""
        while True:
            path = base_dir + "/" + name + extra_txt + extension
            path_disk = OUTPUT_DIRECTORY + "/" + path
            if os.path.exists(path_disk):
                if util.get_file_data(path_disk) == data:
                    break
                else:
                    extra_cnt += 1
                    extra_txt = "-%d" % extra_cnt
            else:
                util.set_file_data(path_disk, data)
                break

    return path


def _promo_image_replacement(img):
    # Four of the images that appear on the sidebar (book promos) also appear
    # in a blog post.  The images are *almost* identical, so with a bit of
    # processing, we can compress the archive.  Replace the promo and post
    # images with the image linked to from the post.
    #
    # See notes/duplicate-book-promo-images.txt

    src = img.attrs["src"]
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("http://"):
        src = "https:" + src[5:]

    STARS_REACH = "https://1.bp.blogspot.com/-mW4_Mvv3LlU/U1Mrk_pz4HI/AAAAAAAAAKE/M_5EWDHNSZo/s1600/Star%27s+Reach+Cover2flat.jpg"
    KINGS_PORT = "https://4.bp.blogspot.com/-GjQHgCY4umk/WCO_UfNAT0I/AAAAAAAAAeU/NI5b7vLS2-M1Ja17ZUCAQqe0yvcFiCKfQCLcB/s1600/Kingsport.jpg"
    AFTER_PROGRESS = "https://4.bp.blogspot.com/-z8hu7awhJQY/VQoXbmmc9-I/AAAAAAAAAT8/bZ-EgZoTIUc/s1600/AfterProgress.jpg"
    COLLAPSE_NOW = "https://2.bp.blogspot.com/-TqXo8j23qcI/VPfHwjTOx_I/AAAAAAAAATc/gIbiS20Yehw/s1600/collapsecover1f.jpg"

    REPLACEMENTS = {
        "https://1.bp.blogspot.com/-1Im1QVW0DPM/U1MknGgHGMI/AAAAAAAAAJ4/2AySXZj6XlY/s1600/Star%2527s%2BReach%2BCover2flat.jpg": STARS_REACH,
        "https://1.bp.blogspot.com/-mW4_Mvv3LlU/U1Mrk_pz4HI/AAAAAAAAAKE/M_5EWDHNSZo/s1600/Star%27s+Reach+Cover2flat.jpg": STARS_REACH,
        "https://1.bp.blogspot.com/-mW4_Mvv3LlU/U1Mrk_pz4HI/AAAAAAAAAKE/M_5EWDHNSZo/s1600/Star's+Reach+Cover2flat.jpg": STARS_REACH,

        "https://4.bp.blogspot.com/-GjQHgCY4umk/WCO_UfNAT0I/AAAAAAAAAeU/NI5b7vLS2-M1Ja17ZUCAQqe0yvcFiCKfQCLcB/s320/Kingsport.jpg": KINGS_PORT,
        "https://4.bp.blogspot.com/-GjQHgCY4umk/WCO_UfNAT0I/AAAAAAAAAeU/NI5b7vLS2-M1Ja17ZUCAQqe0yvcFiCKfQCLcB/s1600/Kingsport.jpg": KINGS_PORT,
        "https://4.bp.blogspot.com/-L5k7A05872s/WCFOKJS8LRI/AAAAAAAAAd4/fA8kTYW9-NAvLc3azbLJtx0iLYS01SzkACK4B/s1600/Kingsport.jpg": KINGS_PORT,

        "https://2.bp.blogspot.com/-LypqmN1FIHs/VD87IK_s9HI/AAAAAAAAAO4/RlhN6nn2gdI/s1600/AfterProgress.jpg": AFTER_PROGRESS,
        "https://4.bp.blogspot.com/-z8hu7awhJQY/VQoXbmmc9-I/AAAAAAAAAT8/bZ-EgZoTIUc/s1600/AfterProgress.jpg": AFTER_PROGRESS,

        "https://2.bp.blogspot.com/-TqXo8j23qcI/VPfHwjTOx_I/AAAAAAAAATc/gIbiS20Yehw/s1600/collapsecover1f.jpg": COLLAPSE_NOW,
        "https://1.bp.blogspot.com/-wuzocRt9Fqg/VPTEvxMbcSI/AAAAAAAAATQ/SWdThliJ8fc/s1600/collapsecover1f.jpg": COLLAPSE_NOW,
    }

    if src in REPLACEMENTS:
        # Keep the original around in the web_cache in case we need it later.
        web_cache.get(img.attrs["src"])
        img.attrs["src"] = REPLACEMENTS[src]
        # Scale both the post image and the sidebar image down to the same
        # size, which will help prevent duplication later on in the image
        # pipeline.
        _set_promo_img_size(img)

    return src


# Convert the FP value to a string like N.Nx, suitable for use in the HTML5 img
# srcset attribute.  Round the FP value to one decimal place.  If the ratio is
# an integral multiple, like 1.0x or 2.0x, then remove the trailing zero.
def _format_srcset_ratio(ratio):
    ret = "%1.1f" % ratio
    if ret.endswith(".0"):
        ret = ret[:-2]
    ret += "x"
    return ret


def _fixup_images_and_hyperlinks(out, url_to_root):
    # Image fixups -- replace delayLoad and //-relative paths.
    _replace_delay_load(out)

    async_image_conversion = []

    # Internalize images.
    for x in out.find_all("img"):
        _promo_image_replacement(x)
        src = x.attrs["src"]
        is_avatar = x.parent.attrs.get("class") == ["avatar-hovercard"]
        image_type = [IMAGE_TYPE_NORMAL, IMAGE_TYPE_AVATAR][is_avatar]
        html_size = (x.attrs.get("width"), x.attrs.get("height"))

        normal_path = None
        hidpi_path = _intern_image_async(src, image_type, html_size, True)
        if is_avatar and hidpi_path is not None:
            # If this was an avatar, then we just use the hidpi image without a
            # srcset.  Avatars are small anyway, and we care about the size of
            # the avatar img-src in the comments' HTML.
            normal_path = hidpi_path
            hidpi_path = None
        else:
            normal_path = _intern_image_async(src, image_type, html_size, False)

        if normal_path is None:
            assert hidpi_path is None
            #print("WARNING: 404 error on image " + src + ": removing img tag")
            x.decompose()
            continue
        async_image_conversion.append((x, "src", normal_path, hidpi_path))

        # If we have an image hyperlink to what appears to be an image itself,
        # hosted on Blogspot, then it's likely an expandable image in the main
        # post body, and it'd make sense to archive it.
        if x.parent.name == "a" and "href" in x.parent.attrs:
            href = x.parent.attrs["href"]
            if re.match(r"(https?:)?//[1234]\.bp\.blogspot\.com/.*\.(png|gif|jpg|jpeg)$", href, re.IGNORECASE):
                path = _intern_image_async(href)
                if path is not None:
                    async_image_conversion.append((x.parent, "href", path, None))

    for (element, attr, normal_path, hidpi_path) in async_image_conversion:
        if hidpi_path is not None:
            assert normal_path is not None
            assert element.name == "img"
            assert attr == "src"
            element.attrs["src"] = url_to_root + "/" + normal_path.get()
            element.attrs["srcset"] = (url_to_root + "/" + hidpi_path.get() + " " +
                _format_srcset_ratio(hidpi_path.hidpi_ratio()))
        else:
            element.attrs[attr] = url_to_root + "/" + normal_path.get()

    # Fixup hyperlinks to https://thearchdruidreport.blogspot.com/
    for x in out.find_all("a"):
        if "href" not in x.attrs:
            continue
        href = str(x.attrs["href"])

        # Fix a typo in: https://thearchdruidreport.blogspot.com/2015/03/planet-of-space-bats.html
        if href == "http://thearchdruidreport.blogspot.com/2011/09/invasion-of-space-bats":
            href = "http://thearchdruidreport.blogspot.com/2011/09/invasion-of-space-bats.html"
            x.attrs["href"] = href

        # Google owns Youtube and blogger.  They seem to prefer //-relative URLs for their own sites.
        if href.startswith("//"):
            href = "https:" + href
            x.attrs["href"] = href

        # Regarding country-specific domains:
        # pcregrep -r 'thearchdruidreport\.blogspot\.(?!(com|com\.au|ca|se|co\.uk|co\.nz|ie|tw|de|jp|ru|ro|fr|no|mx)/)[a-z.]+/' web_cache/thearchdruidreport.blogspot.com | grep 'thearchdruidreport\.blogspot'

        # Link to specific post
        #  - or to the comments of a post
        #  - au hack for https://thearchdruidreport.blogspot.com/2017/02/perched-on-wheel-of-time.html?showComment=1486025128277#c8488642180321946181
        #  - strip %22 (") from the end to work around typos:
        #     - https://thearchdruidreport.blogspot.com/2016/09/retrotopia-only-way-forward.html?showComment=1473304768992#c3850409753902114561
        #     - https://thearchdruidreport.blogspot.com/2016/04/the-end-of-ordinary-politics.html
        #        - WARNING: curious URL in hyperlink: http://thearchdruidreport.blogspot.com/2014/02/fascism-and-future-part-two.html%22
        #     - https://thearchdruidreport.blogspot.com/2016/02/whatever-happened-to-peak-oil.html
        #        - WARNING: curious URL in hyperlink: http://thearchdruidreport.blogspot.com/2014/08/dark-age-america-population-implosion.html%22
        # Another link typo: no http/https scheme in: https://thearchdruidreport.blogspot.com/2015/08/the-war-against-change.html?showComment=1439605715937#c3735987162115847839
        m = re.match(r"^(?:https?://)?thearchdruidreport\.blogspot\.(?:com|com\.au|ca|se|co\.uk|co\.nz|ie|tw|de|jp|ru|ro|fr|no|mx)/(\d\d\d\d/\d\d/.+\.html(#comments)?)(?:%22)?$", href, re.IGNORECASE)
        if m:
            relpath = m.group(1)
            x.attrs["href"] = url_to_root + "/" + relpath
            continue

        # Link to specific post's comment
        m = re.match(r"^https?://thearchdruidreport\.blogspot\.(?:com|com\.au|ca|se|co\.uk|co\.nz|ie|tw|de|jp|ru|ro|fr|no|mx)/(\d\d\d\d/\d\d/.+\.html)\?showComment=\d+\#(c\d+)$", href, re.IGNORECASE)
        if m:
            relpath = m.group(1)
            comment = m.group(2)
            x.attrs["href"] = url_to_root + "/" + relpath + "#" + comment
            continue

        # Link to the toplevel
        if re.match(r"^https?://thearchdruidreport\.blogspot\.com/?$", href, re.IGNORECASE):
            x.attrs["href"] = url_to_root + "/index.html"
            continue

        # Link to commenter's blogger profile (leave them in, I guess)
        if re.match(r"^https?://(?:www|draft)\.blogger\.com/profile/\d+$", href, re.IGNORECASE):
            continue

        # Optimized comment permalink
        if re.match(r"#c\d+$", href):
            continue

        # Anything else?
        if len(x.contents) != 0:
            # If the anchor is empty, just ignore it.  There are too many dumb errors.
            #  - https://thearchdruidreport.blogspot.com/2014/04/refusing-call-tale-rewritten.html
            if ("thearchdruidreport.blogspot." in href) or ("blogger.com" in href) or not (
                        href.startswith("http://") or href.startswith("https://") or
                        href.startswith("javascript:") or href.startswith("../")
                    ):
                print("WARNING: curious URL in hyperlink: %s" % href)
                sys.stdout.flush()


    # I'm not sure whether relative URLs work with these meta tags, so just remove them.
    #
    # for x in out.find_all("meta", itemprop="image_url"):
    #     path = _intern_image(x.attrs["content"])
    #     assert path is not None
    #     x.attrs["content"] = url_to_root + "/" + path
    # for x in out.find_all("meta", itemprop="url"):
    #     m = re.match(r"https?://thearchdruidreport\.blogspot\.com/(.+\.html)$", str(x.attrs["content"]))
    #     assert m is not None
    #     x.attrs["content"] = url_to_root + "/" + m.group(1)
    #
    for x in out.find_all("meta", itemprop="image_url"):
        x.decompose()
    for x in out.find_all("meta", itemprop="url"):
        x.decompose()

    # https://validator.w3.org/nu/ complains about elements not being part of any item.
    for x in out.find_all("meta", itemprop="blogId"):
        x.decompose()
    for x in out.find_all("meta", itemprop="postId"):
        x.decompose()
    for x in out.find_all(lambda tag: "itemprop" in tag.attrs): del x.attrs["itemprop"]
    for x in out.find_all(lambda tag: "itemscope" in tag.attrs): del x.attrs["itemscope"]
    for x in out.find_all(lambda tag: "itemtype" in tag.attrs): del x.attrs["itemtype"]

    # Get rid of "<a name>"; they're obsolete, and the HTML5 validator complains.
    for x in out.find_all("a"):
        if "name" in x.attrs and "href" not in x.attrs and len(x.contents) == 0:
            x.decompose()
            continue
    # validator fix: Error: Attribute imageanchor not allowed on element a at this point
    for x in out.find_all("a"):
        if "imageanchor" in x.attrs:
            del x.attrs["imageanchor"]
    # validator fix: Error: Attribute trbidi not allowed on element div at this point.
    for x in out.find_all("div", trbidi="on"):
        del x.attrs["trbidi"]


def _generate_common(page_url, url_to_root):
    out = _soup(MAIN_TEMPLATE % {"resources" : url_to_root + "/resources"}, None)
    out.select_one("#sidebarbottom-wrap1").replace_with(_gen_sidebar(page_url, url_to_root))
    return out


def generate_single_post(page_url):
    print("Generating page for %s ..." % page_url)
    sys.stdout.flush()

    doc = _page(page_url)
    out = _generate_common(page_url, "../..")
    post_parent = out.select_one(".blog-posts")
    post_parent.append(_gen_blog_post(page_url, True, False))

    # Page navigation
    out.select_one(".blog-pager").replace_with(copy(doc.select_one('.blog-pager')))

    out.title.replace_with(copy(doc.title))
    _fixup_images_and_hyperlinks(out, "../..")
    _write_page(out, OUTPUT_DIRECTORY + ("/%04d/%02d/%s" % parse_tar_url(page_url)))


def generate_month(year, month):
    print("Generating month %04d/%02d ..." % (year, month))
    sys.stdout.flush()

    # Find the posts to include and to link to.
    all_posts = load_posts()
    posts = [p for p in all_posts if (p.year, p.month) == (year, month)]
    if len(posts) == 0:
        return
    older = [(p.year, p.month) for p in all_posts if (p.year, p.month) < (year, month)]
    older = max(older) if len(older) > 0 else None
    newer = [(p.year, p.month) for p in all_posts if (p.year, p.month) > (year, month)]
    newer = min(newer) if len(newer) > 0 else None

    # Generate the document and add the month's posts.
    doc = _page(posts[0].url)
    out = _generate_common(posts[0].url, "../..")
    post_parent = out.select_one(".blog-posts")
    for p in posts:
        post_parent.append(_gen_blog_post(p.url, False, True))

    # Generate the Older/Newer posts pager.
    pager_html = """<div class="blog-pager" id="blog-pager">"""
    if newer is not None:
        pager_html += """
            <span id="blog-pager-newer-link">
                <a class="blog-pager-newer-link" href="../../%04d/%02d/index.html" id="Blog1_blog-pager-newer-link" title="Newer Posts">Newer Posts</a>
            </span>
            """ % newer
    if older is not None:
        pager_html += """
            <span id="blog-pager-older-link">
                <a class="blog-pager-older-link" href="../../%04d/%02d/index.html" id="Blog1_blog-pager-older-link" title="Older Posts">Older Posts</a>
            </span>
            """ % older
    pager_html += """
            <a class="home-link" href="http://thearchdruidreport.blogspot.com/">Home</a>
        </div>
        """
    out.select_one(".blog-pager").replace_with(_soup(pager_html, "div"))

    out.title.string = "The Archdruid Report: %s %04d" % (_month_name(month), year)
    _fixup_images_and_hyperlinks(out, "../..")
    _write_page(out, "%s/%04d/%02d/index.html" % (OUTPUT_DIRECTORY, year, month))


def _write_redirect(path, url):
    util.set_file_text(path,
"""<!DOCTYPE html>
<html>
<head>
<meta http-equiv="refresh" content="0; url=%s" />
</head>
</html>
""" % url)


def generate_redirects():
    all_posts = load_posts()
    for year in sorted(set([p.year for p in all_posts])):
        newest = max([p.month for p in all_posts if p.year == year])
        _write_redirect("%s/%04d/index.html" % (OUTPUT_DIRECTORY, year), "%02d/index.html" % newest)
    newest = max([(p.year, p.month) for p in all_posts])
    _write_redirect(OUTPUT_DIRECTORY + "/index.html", "%04d/%02d/index.html" % newest)


def _generate_posts_js(resources_path):
    all_posts = load_posts()
    lines = []
    lines.append("var blog_archive_posts = {\n")
    for year, month in sorted(set([(p.year, p.month) for p in all_posts]))[::-1]:
        lines.append("'%04d_%02d':[\n" % (year, month))
        for post in [p for p in all_posts if (p.year, p.month) == (year, month)]:
            lines.append('[%s,%s],\n' % (json.dumps(html.escape(post.title, False)), json.dumps(post.page)))
        lines.append("],\n")
    lines.append("};\n")
    util.set_file_text(os.path.join(resources_path, "posts.js"), "".join(lines))


def _intern_css_images(css, base_url):
    ret = []
    i = 0
    p1 = re.compile(r"url\(")
    p2 = re.compile(r"url\(\"([^\+\%\&()\\\"\']+)\"\)")
    p3 = re.compile(r"url\(\'([^\+\%\&()\\\"\']+)\'\)")
    p4 = re.compile(r"url\(([^\+\%\&()\\\"\']+)\)")
    while True:
        s = p1.search(css, i)
        if s is None:
            ret.append(css[i:])
            break
        ret.append(css[i:s.start()])
        i = s.start()
        m = p2.match(css, i) or p3.match(css, i) or p4.match(css, i)
        url = m.group(1)
        if url.startswith("data:"):
            pass
        else:
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = re.match(r"(https?://[^/]+)/", base_url).group(1) + url
            path = _intern_image(url, IMAGE_TYPE_RESOURCE)
            if not path:
                raise RuntimeError("ERROR: _intern_css_images: %s" % url)
            url = "../" + path
        ret.append('url("%s")' % url)
        i = m.end()
    return "".join(ret)


def _gen_resources():
    # Copy the initial template.
    if os.path.exists(OUTPUT_DIRECTORY + "/resources"):
        shutil.rmtree(OUTPUT_DIRECTORY + "/resources")
    if util.mtime("resources/archive_toggle.js") > util.mtime("resources/archive_toggle.min.js"):
        subprocess.check_call(["node_modules/.bin/minify", "resources/archive_toggle.js"])
    util.makedir(OUTPUT_DIRECTORY + "/resources")
    shutil.copyfile("resources/archive_toggle.min.js", OUTPUT_DIRECTORY + "/resources/archive_toggle.js")

    # Pull in the main Blogger template's stylesheet.
    url = "https://thearchdruidreport.blogspot.com/2006/05/real-druids.html"
    style = _page(url).find('style', id="page-skin-1")
    style = re.match(r"^\<\!--(.*)--\>$", str(style.string).strip(), re.DOTALL).group(1).strip()
    style = _intern_css_images(style, url)
    util.set_file_text(os.path.join(OUTPUT_DIRECTORY, "resources", "blogger-page-skin-1.css"), style)

    # Handle extra stylesheets.
    for name, url in [
                ("blogger-authorization.css",       "https://www.blogger.com/dyn-css/authorization.css?targetBlogID=27481991&zx=a190e9d9-9133-4cb6-9d57-1b4c7a2560fd"),
                ("58827200-widget_css_bundle.css",  "https://www.blogger.com/static/v1/widgets/58827200-widget_css_bundle.css"),
            ]:
        style = web_cache.get(url).decode("utf8")
        style = _intern_css_images(style, url)
        util.set_file_text(os.path.join(OUTPUT_DIRECTORY, "resources", name), style)

    # Handle miscellaneous other resources.
    for name, url in [("favicon.ico", "https://thearchdruidreport.blogspot.com/favicon.ico")]:
        util.set_file_data(os.path.join(OUTPUT_DIRECTORY, "resources", name), web_cache.get(url))

    _generate_posts_js(OUTPUT_DIRECTORY + "/resources")


def _generate_everything(apply_):
    if os.path.exists(OUTPUT_DIRECTORY):
        shutil.rmtree(OUTPUT_DIRECTORY)

    # Quick, common stuff
    _gen_resources()
    generate_redirects()

    # Monthly indices
    all_posts = load_posts()
    for y, m in sorted(set([(p.year, p.month) for p in all_posts])):
        apply_(generate_month, (y, m))

    # Individual posts
    for p in all_posts[::-1]:
        apply_(generate_single_post, (p.url,))


def _small_test_run(apply_):
    _gen_resources()
    for year in [2015, 2016]:
        for month in range(1, 13):
            apply_(generate_month, (year, month))
    for p in load_posts():
        if 2015 <= p.year <= 2016:
            apply_(generate_single_post, (p.url,))


def main(apply_):
    #_gen_resources()
    # generate_redirects()
    # for p in load_posts():
    #     if p.year <= 2006:
    #         apply_(generate_single_post, (p.url,))
    #apply_(generate_single_post, ("https://thearchdruidreport.blogspot.com/2009/02/toward-ecosophy.html",))
    # apply_(generate_single_post, ("https://thearchdruidreport.blogspot.com/2013/01/into-unknown-country.html",))
    # apply_(generate_single_post, ("https://thearchdruidreport.blogspot.com/2016/01/donald-trump-and-politics-of-resentment.html",))
    # apply_(generate_single_post, ("https://thearchdruidreport.blogspot.com/2009/12/immodest-proposals.html",))
    # apply_(generate_single_post, ("https://thearchdruidreport.blogspot.com/2006/05/deer-in-headlights.html",))
    # generate_single_post("https://thearchdruidreport.blogspot.com/2009/01/pornography-of-political-fear.html")
    #_small_test_run(apply_)
    _generate_everything(apply_)


def _set_fs_lock(lock):
    global _fs_lock
    _fs_lock = lock
    web_cache.set_fs_lock(lock)
    image_compressor.set_fs_lock(lock)


def _multiproc_init(lock, compressor):
    global _image_compressor
    _image_compressor = compressor
    _set_fs_lock(lock)


class _ImageCompressorManager(multiprocessing.managers.BaseManager):
    pass

_ImageCompressorManager.register("ImageCompressor", image_compressor.ImageCompressor, exposed=[
    "start_compress_async",
    "compress",
    "has_cached",
])


def main_parallel():
    global _image_compressor
    lock = multiprocessing.Lock()
    _set_fs_lock(lock)
    compressor_mgr = _ImageCompressorManager()
    compressor_mgr.start()
    _image_compressor = compressor_mgr.ImageCompressor()

    with multiprocessing.Pool(
            processes=multiprocessing.cpu_count(),
            initializer=_multiproc_init, initargs=(_fs_lock, _image_compressor)) as pool:
        tasks = []
        main(lambda func, args: tasks.append(pool.apply_async(func, args)))
        for t in tasks:
            t.get()


def main_single():
    global _image_compressor
    lock = threading.Lock()
    _set_fs_lock(lock)
    _image_compressor = image_compressor.SyncImageCompressor()

    main(lambda func, args: func(*args))


if __name__ == "__main__":
    #main_single()
    main_parallel()
