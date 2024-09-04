from urllib.parse import parse_qs, urlencode, parse_qsl
from django import template
from django.utils.html import format_html
from html import unescape
from django.utils.safestring import mark_safe
from django.contrib.admin.views.main import PAGE_VAR
import ast
from app.middleware import get_current_request


register = template.Library()

import random



@register.filter(name="has_record_access")
def has_record_access(value, access):
    value_string = [*value]
    if not access:
        value_string = value.replace(' ','*')
        # value_string = [*value_string]
        # for i in range(1, len(value_string), 2):
        #     value_string[i]="*"
        value_string = value_string[:3] + "*****"

    return ''.join(value_string)

DOT = '.'


@register.simple_tag
def custom_paginator_number(cl, i):
    """
    Generate an individual page index link in a paginated list.
    """
    page_number = ''
    if get_current_request() and 'page_size' in parse_qs(get_current_request().META.get('QUERY_STRING')):
        page_number = '&page_size='+ ','.join(parse_qs(get_current_request().META.get('QUERY_STRING')).get('page_size'))
    if i == cl.paginator.ELLIPSIS:
        return format_html('{} ', cl.paginator.ELLIPSIS)
    elif int(i) == cl.page_num:
        return format_html('<span class="this-page">{}</span> ', int(i))
    else:
        return format_html(
            '<a href="{}"{}>{}</a> ',
            cl.get_query_string({PAGE_VAR: i}) + page_number,
            mark_safe(' class="end"' if int(i) == cl.paginator.num_pages - 1 else ''),
            int(i),
        )
    

@register.simple_tag
def custom_page_query(cl):
    """
    Generate an individual page index link in a paginated list.
    """
    page_number = ''
    if cl.get_query_string():
        page_number = cl.get_query_string() + '&'
        
    return page_number


@register.filter(name="format_html_data")
def format_html_data(value):
    return format_html(unescape(value))


@register.filter(name="obj_field_list")
def obj_field_list(obj, field):
    return getattr(obj, field)



@register.filter(name="obj_field_list_eval")
def obj_field_list_eval(obj, field):
    return ast.literal_eval(obj_field_list(obj, field))