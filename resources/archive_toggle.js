var archive_toggle = (function() {

    var arc_populated_already = {};

    function get_month_name(month) {
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
        ][month - 1];
    }

    function get_month_2dig(month) {
        var ret = month + "";
        if (ret.length == 1) {
            ret = "0" + ret;
        }
        return ret;
    }

    function get_month_id(year, month) {
        return year + "_" + get_month_2dig(month);
    }

    function archive_toggle(id) {
        var e = document.getElementById("arc_" + id);
        var es = e.getElementsByTagName("span")[0];
        if (e.className.match(/\bexpanded\b/)) {
            e.className = "collapsed";
            es.innerHTML = "►&nbsp;";
            arc_populated_already[id] = true;
        } else {
            e.className = "expanded";
            es.innerHTML = "▼&nbsp;";
            if (!arc_populated_already[id]) {
                arc_populated_already[id] = true;
                if (id.match(/^\d\d\d\d$/)) {
                    // Expand this year.
                    var newhtml = "";
                    for (var month = 12; month >= 1; --month) {
                        var month_id = get_month_id(id, month);
                        if (!(month_id in blog_archive_posts)) {
                            continue;
                        }
                        var count = blog_archive_posts[month_id].length;
                        var index_url = '../../' + id + '/' + get_month_2dig(month) + '/index.html';
                        newhtml +=
                            '<ul>' +
                                '<li class="collapsed" id="arc_' + month_id + '">' +
                                    '<a class="toggle" onclick="archive_toggle(\'' + month_id + '\')" href="javascript:void(0)">' +
                                        '<span>►&nbsp;</span>' +
                                    '</a>' +
                                    '<a class="post-count-link" href="' + index_url + '">' +
                                        get_month_name(month) +
                                    '</a> (' + count + ') ' +
                                    '<ul class="posts"></ul> ' +
                                '</li> ' +
                            '</ul>';
                    }
                    e.innerHTML += newhtml;
                }
                if (id.match(/^\d\d\d\d_\d\d$/)) {
                    // Expand this month.
                    var ep = e.getElementsByTagName("ul")[0];
                    var posts = blog_archive_posts[id];
                    var newhtml = "";
                    for (var i = 0; i < posts.length; ++i) {
                        var title = posts[i][0];
                        var url = "../../" + id.replace("_", "/") + "/" + posts[i][1];
                        newhtml += '<li><a href="' + url + '">' + title + '</li>\n';
                    }
                    ep.innerHTML = newhtml;
                }
            }
        }
    }

    return archive_toggle;
})();

function init_archive_widget() {
    var top = document.getElementById("BlogArchive1_ArchiveList");
    var elements = top.getElementsByTagName("li");
    for (var i = 0; i < elements.length; ++i) {
        var e = elements[i];
        var m = null;
        if (m = e.id.match(/^arc_(\d\d\d\d(_\d\d)?)$/)) {
            var es = e.getElementsByTagName("span")[0];
            es.outerHTML = '<a class="toggle" onclick="archive_toggle(\'' + m[1] + '\')" href="javascript:void(0)">' + es.outerHTML + '</a>';
        }
    }
}
