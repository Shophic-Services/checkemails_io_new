from http.client import HTTPResponse
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.encoding import force_str
from django.db.models import Q
from app.middleware import get_current_user
from import_export.admin import ExportMixin
from import_export.formats.base_formats import CSV, XLSX
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy


class CheckEmailsBaseModelAdmin(admin.ModelAdmin):
    '''
    Custom Base model admin which contains a delete action
    and other model admin helper methods 
    '''
    class_error = None
    empty_value_display = '-'
    ordering = ('-modify_date', )
    list_per_page = 20
    list_page = [50,100,500,1000,10000]
    # actions = None

    def action(self, obj):
        _ = self.class_error
        if hasattr(obj, 'can_change') and not obj.can_change:
            return '-'
        url = reverse(
                'admin:%s_%s_delete' % (obj._meta.app_label, obj._meta.model_name), 
                args=[force_str(obj.pk)]
            ) 
        return format_html('<a class="btn" onClick="return window.confirm(\'Deleting this {} would delete its respective references and this action cannot be reversed. Are you sure you want to proceed?\')" href="{}">Delete</a>', str(obj), url)
    
    def get_field_queryset(self, db, db_field, request):
        initial_queryset = super(CheckEmailsBaseModelAdmin, self).get_field_queryset(db, db_field, request)
        try:
            initial_queryset = initial_queryset.filter(is_deleted=False)
        except:
            pass
        return initial_queryset
    
    def has_delete_permission(self, request, obj=None):
        _ = self.class_error
        path = request.path
        model_action = path.split('/')[-2]
        if model_action == 'change':
            return False 
        else:
            return True
    
    def save_model(self, request, obj, form, change):
        """
        Save Model method for model admin
        """
        if not change:
            obj.added_by_id = request.user.id
        else:
            obj.modified_by_id = request.user.id
        
        return super(CheckEmailsBaseModelAdmin, self).save_model(
                                        request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        _ = self
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if instance.id:
                instance.modified_by_id = request.user.id
            else:
                instance.added_by_id = request.user.id
            instance.save()
        formset.save_m2m()
    
    def get_queryset(self, request):
        initial_queryset = super(CheckEmailsBaseModelAdmin, self).get_queryset(request).filter(is_deleted=False)
        return initial_queryset

    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        self.list_per_page = int(request.GET.get('page_size',50))
        if self.list_per_page not in self.list_page:
            return HttpResponseRedirect(reverse_lazy('admin:'+ self.model._meta.app_label + '_' +self.model._meta.model_name +'_changelist'))
        extra_context.update({'page_size': self.list_per_page,
        'page_sizes':self.list_page})
        if not request.GET._mutable:
            request.GET._mutable = True
            request.GET.pop('page_size',None)
            request.GET._mutable = False
        return super(CheckEmailsBaseModelAdmin, self).\
            changelist_view(request, extra_context=extra_context)

