var arc_tog = (function() {

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

    function arc_tog(id) {
        var e = document.getElementById("arc_" + id);
        var es = e.getElementsByTagName("span")[0];
        if (e.classList.contains("expanded")) {
            e.className = "archivedate collapsed";
            es.className = "zippy";
            es.innerHTML = "►&nbsp;";
            arc_populated_already[id] = true;
        } else {
            e.className = "archivedate expanded";
            es.className = "zippy toggle-open";
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
                            '<ul class="hierarchy">' +
                                '<li class="archivedate collapsed" id="arc_' + month_id + '">' +
                                    '<a class="toggle" onclick="arc_tog(\'' + month_id + '\')" href="javascript:void(0)">' +
                                        '<span class="zippy">►&nbsp;</span>' +
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

    return arc_tog;
})();
