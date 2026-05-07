from django.contrib import admin
from tools.models import DataSourceItem, EmailData, DataSourceJob, LeadFinder, ScraperResult, SpamCategory
from django.utils.html import format_html
# Register your models here.

class EmailDataAdmin(admin.ModelAdmin):
    list_display = ('email', 'email_result','status','catchall','added_by', 'create_date')
    search_fields = ('email',)

    fieldsets = (
        (None, {
            'fields': (
                'email', 'role_based', 'has_domain_mx', 'has_spf', 'has_dmarc',
                'status', 'quality', 'email_result', 'valid', 'email_source',
                'catch_all', 'email_type', 'code', 'retry_later',
                'permanent_failure', 'needs_manual_review', 'has_smtp',
                'output'
            )
        }),
    )
    readonly_fields = (
        'email', 'role_based', 'has_domain_mx', 'has_spf', 'has_dmarc',
        'status', 'quality', 'email_result', 'valid', 'email_source',
        'catch_all', 'email_type', 'code', 'retry_later',
        'permanent_failure', 'needs_manual_review', 'has_smtp','output'
    )

    def output(self, obj):
        if not obj.message:
            return '-'
        message_obj = obj.message.replace('\\n', '<br>')

        from django.utils.safestring import mark_safe
        print(message_obj)
        return mark_safe(
            '<pre style="white-space: pre-wrap; font-size:12px;">' + message_obj + '</pre>'
            
        )

    output.short_description = 'Output'


    def catchall(self, obj):
        return format_html('<img src="/static/admin/img/icon-yes.svg" alt="True">') if obj.catch_all else '-'
    catchall.boolean = False
    catchall.short_description = 'Catch-All'


admin.site.register(EmailData, EmailDataAdmin)
admin.site.register(LeadFinder)
admin.site.register(DataSourceJob)
admin.site.register(DataSourceItem)
admin.site.register(SpamCategory)
admin.site.register(ScraperResult)


