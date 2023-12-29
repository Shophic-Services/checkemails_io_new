from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.encoding import force_str
from checkemails.core.admin import CheckEmailsBaseModelAdmin
from checkemails.core.widgets import CustomRelatedDropdownFilter
from emailtool.models import EmailSearch, SpamCategory, SpamKeyword
from import_export.admin import ExportActionMixin
from import_export.formats.base_formats import CSV, XLSX
from emailtool.model_resources import EmailSearchResource
from datetime import datetime
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)


class InlineSpamKeywordModelAdmin(admin.TabularInline):
    model = SpamKeyword
    fields = ('keyword','regex_pattern')
    extra = 0

class SpamCategoryAdmin(CheckEmailsBaseModelAdmin):
    list_display = ['title', 'get_keyword_count','action_button']
    
    fields = ('title',)

    inlines = (InlineSpamKeywordModelAdmin,)
    def get_keyword_count(self, obj):
        _ = self
        return SpamKeyword.objects.filter(category=obj).count()
    get_keyword_count.short_description = 'Number of Keyword'
    get_keyword_count.allow_tags = True
        
    def action_button(self, obj):
        view_url = reverse(
                'admin:%s_%s_change' % (self.model._meta.app_label, self.model._meta.model_name), 
                args=[force_str(obj.pk)]
            )
        return format_html('<a class="change-related" href="{}"><img src="/static/images/icon-viewlink.svg"></a></a>', view_url)

    action_button.short_description = 'Action'
    list_display_links = None
    readonly_fields = ['title']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_edit_permission(self, request, obj=None):
        return False

class EmailSearchAdmin(ExportActionMixin, CheckEmailsBaseModelAdmin):
    list_display = ['email_address', 'verified','code', 'message', 'added_by', 'modify_date',]
    ordering = ['modify_date']
    
    list_display_links = None
    list_filter = (('added_by', CustomRelatedDropdownFilter),('modify_date',DateRangeFilterBuilder()),'verified','code')
    search_fields = ( 'email_address',)
    resource_class  = EmailSearchResource
    formats = (CSV, XLSX,)
    
    def get_export_filename(self, request, queryset, file_format):
            date_str = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
            filename = "Check-emails-%s.%s" % (
                                    date_str,
                                    file_format.get_extension())
            return filename

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_edit_permission(self, request, obj=None):
        return False

admin.site.register(EmailSearch, EmailSearchAdmin)


admin.site.register(SpamCategory, SpamCategoryAdmin)