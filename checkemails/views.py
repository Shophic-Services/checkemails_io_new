from django.template.loader import get_template
from django.http import HttpResponseServerError
from checkemails.core.context_processors import load_user_data

BASE_WITH_LOGIN_HTML = 'layouts/base_with_login.html'
BASE_WITHOUT_LOGIN_HTML = 'layouts/base_without_login.html'

def server_error(request, template_name='500.html'):
    context=load_user_data(request)
    context['error']=True
    if request.user.is_authenticated:
        base_template = BASE_WITH_LOGIN_HTML
    else:
        base_template = BASE_WITHOUT_LOGIN_HTML
    context.update({'base_template': base_template})
    t = get_template(template_name)
    return HttpResponseServerError(t.render(context))

class HttpResponseForbidden(HttpResponseServerError):
    status_code = 403

def permission_denied(request, exception, template_name='403.html'):
    context=load_user_data(request)
    context['error']=True
    if request.user.is_authenticated:
        base_template = BASE_WITH_LOGIN_HTML
    else:
        base_template = BASE_WITHOUT_LOGIN_HTML
    context.update({'base_template': base_template})
    t = get_template(template_name)
    return HttpResponseForbidden(t.render(context))

class HttpResponseNotFound(HttpResponseServerError):
    status_code = 404

def page_not_found(request, exception, template_name='404.html'):
    context=load_user_data(request)
    context['error']=True
    if request.user.is_authenticated:
        base_template = BASE_WITH_LOGIN_HTML
    else:
        base_template = BASE_WITHOUT_LOGIN_HTML
    context.update({'base_template': base_template})
    t = get_template(template_name)
    return HttpResponseNotFound(t.render(context))


def csrf_failure(request, reason="", template_name='403_csrf.html'):
    """
    Default view used when request fails CSRF protection
    """
    context=load_user_data(request)
    context['error']=True
    if request.user.is_authenticated:
        base_template = BASE_WITH_LOGIN_HTML
    else:
        base_template = BASE_WITHOUT_LOGIN_HTML
    context.update({'base_template': base_template})
    t = get_template(template_name)
    return HttpResponseForbidden(t.render(context))
