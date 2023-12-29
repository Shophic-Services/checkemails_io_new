(function($){
    $.fn.django_admin_global_sidebar = function(options){
        var settings = $.extend({
            collapse_button: ".django-admin-global-sidebar-collapse-button"
        }, options);
        return $(this).each(function(){
            var root = $(this);
            var collapse_button = null;
            if(settings.collapse_button instanceof $){
                collapse_button = settings.collapse_button;
            }else{
                collapse_button = root.find(settings.collapse_button);
            }
            collapse_button.click(function(){
                if(root.hasClass("django-admin-global-sidebar-collapsed")){
                    root.trigger("expanded");
                }else{
                    root.trigger("collapsed");
                }
            });
            root.find("li").hover(function(){
                $(this).addClass("on");
            },function(){
                $(this).removeClass("on");
            });
            root.find(".django-admin-global-sidebar-submenu").each(function(){
                $(this).prev().click(function(){
                    var li = $(this).parents("li");
                    var button = li.find(".django-admin-global-sidebar-submenu-toggle-button");
                    if(li.hasClass("open")){
                        li.removeClass("open");
                        button.removeClass("fa-chevron-up");
                        button.addClass("fa-chevron-down");
                    }else{
                        li.addClass("open");
                        button.removeClass("fa-chevron-down");
                        button.addClass("fa-chevron-up");
                    }
                });
            });
            root.on("expanded", function(){
                var body = $(document.body);
                var collapse_button_icon = collapse_button.find("i");
                root.find(">ul >li").each(function(){
                    if($(this).hasClass("open-but-collapsed")){
                        $(this).removeClass("open-but-collapsed");
                        $(this).addClass("open");
                    }
                });
                body.removeClass("with-django-admin-global-sidebar-collapsed");
                root.removeClass("django-admin-global-sidebar-collapsed");
                collapse_button_icon.removeClass("fa-indent");
                collapse_button_icon.addClass("fa-outdent");
                $.removeCookie("django-admin-global-sidebar-collapsed-flag", {path: "/"});
            });
            root.on("collapsed", function(){
                var body = $(document.body);
                var collapse_button_icon = collapse_button.find("i");
                root.find(">ul >li").each(function(){
                    if($(this).hasClass("open")){
                        $(this).removeClass("open");
                        $(this).addClass("open-but-collapsed");
                    }
                });
                body.addClass("with-django-admin-global-sidebar-collapsed");
                root.addClass("django-admin-global-sidebar-collapsed");
                collapse_button_icon.removeClass("fa-outdent");
                collapse_button_icon.addClass("fa-indent");
                $.cookie("django-admin-global-sidebar-collapsed-flag", "true", {path: "/"});
            });
        });
    };

    var fix_element_pos_and_height = function(){
        var header_height = $("#header").outerHeight();
        var breadcrumbs_height = $("#container > .breadcrumbs").outerHeight();
        var content_height = $("#container").outerHeight();
        $("#django-admin-global-sidebar").css("top", header_height + "px");
        $("#django-admin-global-sidebar .django-admin-global-sidebar-collapse-button").css("height", breadcrumbs_height + "px");
        $("#django-admin-global-sidebar").css("height", content_height + "px");
    };

    $(document).ready(function(){
        $("#django-admin-global-sidebar").django_admin_global_sidebar();
        $(window).resize(fix_element_pos_and_height);
        window.setTimeout(fix_element_pos_and_height, 50);
    });

})(jQuery);
