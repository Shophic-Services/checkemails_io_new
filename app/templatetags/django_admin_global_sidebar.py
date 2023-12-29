from django import template
from django.template.loader import render_to_string
from app.utils import get_menu_url
from app.utils import get_user_menus

register = template.Library()


@register.simple_tag
def django_admin_global_sidebar_body_classes(request):
    # get django_admin_global_sidebar_menus
    django_admin_global_sidebar_menus = getattr(request, "django_admin_global_sidebar_menus", None)
    if django_admin_global_sidebar_menus is None:
        django_admin_global_sidebar_menus = get_user_menus(request)
        setattr(request, "django_admin_global_sidebar_menus", django_admin_global_sidebar_menus)
    # get django_admin_global_sidebar_collapsed_flag
    django_admin_global_sidebar_collapsed_flag = False
    # get classes
    classes = []
    if django_admin_global_sidebar_menus:
        classes.append("with-django-admin-global-sidebar")
        if django_admin_global_sidebar_collapsed_flag:
            classes.append("with-django-admin-global-sidebar-collapsed")
    return " ".join(classes)

@register.simple_tag
def django_admin_global_sidebar(request):
    # get django_admin_global_sidebar_menus
    django_admin_global_sidebar_menus = getattr(request, "django_admin_global_sidebar_menus", None)
    if django_admin_global_sidebar_menus is None:
        django_admin_global_sidebar_menus = get_user_menus(request)
        setattr(request, "django_admin_global_sidebar_menus", django_admin_global_sidebar_menus)
    # get django_admin_global_sidebar_collapsed_flag
    django_admin_global_sidebar_collapsed_flag = False
    # rendering
    return render_to_string("admin/django-admin-global-sidebar.html", {
        "django_admin_global_sidebar_menus": django_admin_global_sidebar_menus,
        "django_admin_global_sidebar_collapsed_flag": django_admin_global_sidebar_collapsed_flag,
    }, request=request)


@register.simple_tag
def menu_url(menu):
    return get_menu_url(menu) or "javascript:void(0)"
