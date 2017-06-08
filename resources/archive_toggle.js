function arc_tog(id) {
    var e = document.getElementById("arc_" + id);
    var es = e.getElementsByTagName("span")[0];
    var ep = e.getElementsByTagName("ul")[0];
    if (e.classList.contains("expanded")) {
        e.className = "archivedate collapsed";
        es.className = "zippy";
        es.innerHTML = "►&nbsp;";
    } else {
        if (id in blog_archive_posts) {
            if (ep.getElementsByTagName("li").length == 0) {
                var posts = blog_archive_posts[id];
                var newhtml = "";
                for (var i = 0; i < posts.length; ++i) {
                    var title = posts[i][0];
                    var url = "../../" + posts[i][1];
                    newhtml += '<li><a href="' + url + '">' + title + '</li>\n';
                }
                ep.innerHTML = newhtml;
            }
        }
        e.className = "archivedate expanded";
        es.className = "zippy toggle-open";
        es.innerHTML = "▼&nbsp;";
    }
}
