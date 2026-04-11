
var loding = true;
var loded = false;
var seourl = location.href.replace(/[\\#,+()$~%.":*<>{};]/g, '_');
var scripcode;
var type;
var type1;
if (seourl.indexOf('=') == -1) {
    var a = seourl.split('/')
    scripcode = a[6];
    type = a[5];
    type1 = a[4];
}


function LeftMenu(mid, sid, count) {
    //alert(mid); alert(sid); alert(count);
    ////for (i = 1; i < 17; i++)
    ////{
    ////    $("#l" +i).removeClass("panel-active");
    ////    $("#l" + i).addClass("panel-default");
    ////}
    ////if (sid > 0)
    ////{
    ////    var j = parseInt(sid) + parseInt(sicountd);
    ////    for (m = 1; m <= count; m++) {
    ////        var k = toString(sid) + toString(m);
    ////        $("#l" + k).removeClass("panel-active");
    ////        $("#l" + i).addClass("panel-default");
    ////    }
    ////    $("#l" + sid).removeClass("panel-default");
    ////    $("#l" + sid).addClass("panel-active");
    ////}
    //$("#l" + mid).removeClass("panel-default");
    //$("#l" + mid).addClass("panel-active");
    //if (type == "derivatives")
    //{
    //    $("#l2").removeClass("panel-default");
    //    $("#l2").addClass("panel-active");
    //}
    //if (type1 == "debt-other") {
    //    $("#l3").removeClass("panel-default");
    //    $("#l3").addClass("panel-active");
    //}
    //if (type1 == "slb") {
    //    $("#l4").removeClass("panel-default");
    //    $("#l4").addClass("panel-active");
    //}
}


function NewLeftMenu(mid, dis) {
    $("#l1").removeClass("dropdown mega-dropdown default");
    $("#l1").addClass("dropdown mega-dropdown landingsec");
    $("#l2").removeClass("panel-active");
    $("#l2").addClass("panel-default");
    $("#l3").removeClass("panel-active");
    $("#l3").addClass("panel-default");
    $("#l4").removeClass("panel-active");
    $("#l4").addClass("panel-default");
    $("#l5").removeClass("panel-active");
    $("#l5").addClass("panel-default");
    $("#l8").removeClass("panel-active");
    $("#l8").addClass("panel-default");
    $("#l9").removeClass("panel-active");
    $("#l9").addClass("panel-default");
    $("#l10").removeClass("panel-active");
    $("#l10").addClass("panel-default");
    $("#l11").removeClass("panel-active");
    $("#l11").addClass("panel-default");
    $("#l12").removeClass("panel-active");
    $("#l12").addClass("panel-default");
    $("#l13").removeClass("panel-active");
    $("#l13").addClass("panel-default");
    $("#l14").removeClass("panel-active");
    $("#l14").addClass("panel-default");

    $("#l15").removeClass("panel-active");
    $("#l15").addClass("panel-default");
    $("#l16").removeClass("panel-active");
    $("#l16").addClass("panel-default");
    $("#l17").removeClass("panel-active");
    $("#l17").addClass("panel-default");
    $("#l18").removeClass("panel-active");
    $("#l18").addClass("panel-default");
    $("#l22").removeClass("panel-active");
    $("#l22").addClass("panel-default");

    $("#l101").removeClass("panel-active");
    $("#l101").addClass("panel-default");
    $("#l102").removeClass("panel-active");
    $("#l102").addClass("panel-default");
    $("#l103").removeClass("panel-active");
    $("#l103").addClass("panel-default");
    $("#l104").removeClass("panel-active");
    $("#l104").addClass("panel-default");

    $("#l130").removeClass("panel-active");
    $("#l130").addClass("panel-default");
    //new added for sdd shp - shweta
    $("#l99").removeClass("panel-active");
    $("#l99").addClass("panel-default");
    //new added for integrated filing - shweta
    $("#l999").removeClass("panel-active");
    $("#l999").addClass("panel-default");

    $("#l202").removeClass("panel-active");
    $("#l202").addClass("panel-default");


    if (mid == 1) {
        $("#l1").removeClass("dropdown mega-dropdown default");
        $("#l1").addClass("dropdown mega-dropdown landingsec");
    }

    else {

        $("#l" + mid).removeClass("panel-default");
        $("#l" + mid).addClass("panel-active");
    }
    if (dis == "afi") {
        document.getElementById("collapse6").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse2").style.display = "block";
    }
    else if (dis == "ame") {
        document.getElementById("collapse6").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "block";
    }
    else if (dis == "adi") {
        document.getElementById("collapse6").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse4").style.display = "block";
    }
    else if (dis == "mfp") {
        document.getElementById("collapse6").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse5").style.display = "block";
    }
    else if (dis == "ifp") {
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse6").style.display = "block";
    }
    else {
        document.getElementById("collapse6").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
    }
}


function displaymenu(dis) {
    if (dis == "afi") {
        if (document.getElementById("collapse2").style.display == "block") {
            document.getElementById("collapse2").style.display = "none";
            return false;
        }

        document.getElementById("collapse2").style.display = "block";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse6").style.display = "none";
    }
    if (dis == "ame") {
        if (document.getElementById("collapse3").style.display == "block") {
            document.getElementById("collapse3").style.display = "none";
            return false;
        }
        document.getElementById("collapse3").style.display = "block";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse6").style.display = "none";
    }

    if (dis == "adi") {
        if (document.getElementById("collapse4").style.display == "block") {
            document.getElementById("collapse4").style.display = "none";
            return false;
        }
        document.getElementById("collapse4").style.display = "block";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
        document.getElementById("collapse6").style.display = "none";
    }
    if (dis == "mfp") {
        if (document.getElementById("collapse5").style.display == "block") {
            document.getElementById("collapse5").style.display = "none";
            return false;
        }
        document.getElementById("collapse5").style.display = "block";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse6").style.display = "none";
    }
    if (dis == "ifp") {
        if (document.getElementById("collapse6").style.display == "block") {
            document.getElementById("collapse6").style.display = "none";
            return false;
        }
        document.getElementById("collapse6").style.display = "block";
        document.getElementById("collapse2").style.display = "none";
        document.getElementById("collapse3").style.display = "none";
        document.getElementById("collapse4").style.display = "none";
        document.getElementById("collapse5").style.display = "none";
    }
}

function scropup() {
    $([document.documentElement, document.body]).animate({
        scrollTop: $("#equity").offset().top
    }, 0);
    console.log("scropup");
}

$(document).ready(function () {
    console.log("stk equity-ready!");
    var wt = $(window).width();
    if (wt >= 480) {
        var x = document.getElementById("idaside").className;
        if (x === "sidebar perfectScrollbar show") {
            $("#idaside").removeClass("sidebar perfectScrollbar show");
            $("#idaside").addClass("sidebar perfectScrollbar show");
            $("#divmain").removeClass("body slide");
            $("#divmain").addClass("body slide");
        }
        else {
            $("#idaside").removeClass("sidebar perfectScrollbar");
            $("#idaside").addClass("sidebar perfectScrollbar show");
            $("#divmain").removeClass("body");
            $("#divmain").addClass("body slide");
        }
    }
});