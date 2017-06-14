# thearchdruidreport-archive

This repository contains a Python program that downloads the Archdruid Report
blog, currently hosted at https://thearchdruidreport.blogspot.com, and
generates a read-only static version of the site.

## Summary

The archiver currently produces a directory, `thearchdruidreport-archive`,
containing:

 - One HTML page for each post containing all comments consolidated on
   one page.  (HTML anchors include `#comments` and, for each comment, a
   `#c<commentID>` anchor.)

 - One HTML page for each month containing all the posts in that month but
   no comments.

 - One HTML page for each year (`20nn/index.html`) redirecting to the last
   month of the year having a post.

 - A top-level page (`index.html`) redirecting to the last month with a post
   (i.e. May 2017).

The resulting site archive can be viewed on a browser or hosted on a server
somewhere.  Most links that were valid (e.g. posts and comments) for
https://thearchdruidreport.blogspot.com should remain valid for the static
archive, once the domain change is accounted for.

## Technical Details

The program uses the BeautifulSoup4 library to parse and edit HTML documents.
It removes Blogger admin controls, social media sharing buttons, comment
posting controls, etc.  It (should) remove all of the original JavaScript,
substituting just enough ad hoc JavaScript to operate the blog archive tree
widget.  (Rather than use AJAX calls for the widget, though, the static site
uses a `resources/posts.js` file listing every post.)

The program keeps a separate "web_cache" directory recording each HTTP
request used during the archival process, which allows the program to be rerun
without hammering Blogger's servers and allows it to be rerun when the site
goes down.

This program currently archives only the desktop version of the site, and only
the "Blogger Rounders 4"-themed pages (i.e. the pages with the light green
background).  It doesn't archive the mobile pages or the white-backgrounded
comments pages (e.g. https://www.blogger.com/comment.g?blogID=27481991&postID=5178643773481630823).
I might try to add some of these pages to "web_cache" before the site goes
away.

### Dependencies

This program uses Python 3 and a number of Python 3 packages:
```
pip3 install beautifulsoup4
pip3 install lxml
pip3 install requests
pip3 install pillow
```

The program also uses node.js to minify a script.  I tested with
node.js v6.11.0, the LTS release as of this writing.  Ensure that `node` and
`npm` are in your PATH, then run:

```
cd thearchdruidreport-archive
npm install
```

The archiver uses guetzli to compress images.  Initially, it used
version f3e83a7058 of https://github.com/google/guetzli (about 3 months newer
than 1.0.1, which is the latest release as of this writing, 2017-06-11).  Make
sure `guetzli` is in your PATH.

I usually run the program on Linux, but I briefly tested it on Windows, too,
using a native/non-Cygwin Python 3.  The archiver is careful to use only
portable filenames (e.g. short, lowercase, a limited subset of ASCII
characters, no trailing/following periods).

### Running the script

Unix (Linux, macOS, BashOnWindows, or Cygwin):

 * Satisfy dependencies above.  (Make sure `python3`, `node`, `npm`, and
   `guetzli` are in your PATH.  Install the PIP packages and NPM packages.)

 * Run `make-archive.sh`:

   ```
   cd thearchdruidreport-archive
   ./make-archive.sh
   ```

Windows:

 * Install Python 3, node.js, guetzli, and the PIP/NPM packages above, then
   imitate `make_archive.sh`.  Something like this ought to work:

   ```
   cd thearchdruidreport-archive
   C:\<path-to-python3>\python.exe generate_posts_json.py
   C:\<path-to-python3>\python.exe populate_web_cache.py
   C:\<path-to-python3>\python.exe generate_pages.py
   ```
