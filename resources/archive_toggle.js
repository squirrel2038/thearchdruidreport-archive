function init_archive_widget(){for(var e=document.getElementById("BlogArchive1_ArchiveList"),a=e.getElementsByTagName("li"),r=0;r<a.length;++r){var n=a[r],t=null
if(t=n.id.match(/^arc_(\d\d\d\d(_\d\d)?)$/)){var l=n.getElementsByTagName("span")[0]
l.outerHTML='<a class="toggle" onclick="archive_toggle(\''+t[1]+'\')" href="javascript:void(0)">'+l.outerHTML+"</a>"}}}var archive_toggle=function(){function e(e){return["January","February","March","April","May","June","July","August","September","October","November","December"][e-1]}function a(e){var a=e+""
return 1==a.length&&(a="0"+a),a}function r(e,r){return e+"_"+a(r)}function n(n){var l=document.getElementById("arc_"+n),i=l.getElementsByTagName("span")[0]
if(l.className.match(/\bexpanded\b/))l.className="collapsed",i.innerHTML="►&nbsp;",t[n]=!0
else if(l.className="expanded",i.innerHTML="▼&nbsp;",!t[n]){if(t[n]=!0,n.match(/^\d\d\d\d$/)){for(var c="",s=12;s>=1;--s){var o=r(n,s)
if(o in blog_archive_posts){var d=blog_archive_posts[o].length,g="../../"+n+"/"+a(s)+"/index.html"
c+='<ul><li class="collapsed" id="arc_'+o+'"><a class="toggle" onclick="archive_toggle(\''+o+'\')" href="javascript:void(0)"><span>►&nbsp;</span></a><a class="post-count-link" href="'+g+'">'+e(s)+"</a> ("+d+') <ul class="posts"></ul> </li> </ul>'}}l.innerHTML+=c}if(n.match(/^\d\d\d\d_\d\d$/)){for(var u=l.getElementsByTagName("ul")[0],v=blog_archive_posts[n],c="",h=0;h<v.length;++h){var m=v[h][0],p="../../"+n.replace("_","/")+"/"+v[h][1]
c+='<li><a href="'+p+'">'+m+"</li>\n"}u.innerHTML=c}}}var t={}
return n}()
