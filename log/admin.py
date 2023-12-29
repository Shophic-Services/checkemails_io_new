'''
admin for logs
'''
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db import models
from django.forms import Textarea, TextInput

from log.models import Log
from django.utils.html import format_html


class NullListFilter(SimpleListFilter):
    '''
    null list filter
    '''
    def lookups(self, request, model_admin):
        self.request = request
        return (
            ('1', 'Success', ),
            ('0', 'Execption', ),
        )

    def queryset(self, request, queryset):
        if self.value() in ('0', '1'):
            kwargs = {
                '{0}__isnull'.format(self.parameter_name): self.value() == '1'}
            return queryset.filter(**kwargs)
        return queryset


def null_filter(field, title_=None):
    '''
    null filter
    '''
    class NullListFieldFilter(NullListFilter):
        '''
        Null List Field Filter
        '''
        parameter_name = field
        title = title_ or parameter_name
    return NullListFieldFilter


class LogAdmin(admin.ModelAdmin):
    '''
    log admin
    '''
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '20'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 20})},
    }

    def has_add_permission(self, request, obj=None):
        _ = self
        return False

    def has_delete_permission(self, request, obj=None):
        _ = self
        return False

    def has_change_permission(self, request, obj=None):
        _ = self
        return False

    your_fields = Log._meta.local_fields
    readonly_fields = [f.name for f in your_fields]

    lst_of_field_names = [f.name for f in your_fields]
    lst_of_field_names.remove('request_content')
    lst_of_field_names.remove('response_content')
    list_display = ['method_type', 'method_name', 'short_request_content',
                    'short_response_content', 'total_time_taken', 'request_datetime'
                    , 'response_datetime']
    list_per_page = 500
    list_filter = ('response_status_type', 'method_type',
                   null_filter('exception_full_stack_trace'),)

admin.site.register(Log, LogAdmin)

