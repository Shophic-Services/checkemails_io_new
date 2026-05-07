from django.contrib import admin
from django.db.models import Q
from django import forms
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from django.utils.translation import gettext_lazy as _

class BaseInputFilter(admin.SimpleListFilter):
    template = 'admin/filters/input_filter.html'
    parameter_name = None
    title = None
    
    def __init__(self, request, params, model, model_admin):
        self.lookup_kwarg = '%s__iexact' % self.parameter_name
        super().__init__(request, params, model, model_admin)
    
    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice
    
    def queryset(self, request, queryset):
        term = self.value()

        if term is None:
            return

        any_name = Q()
        
        any_name &= (
                Q(**{self.lookup_kwarg:term}) 
            )
        return queryset.filter(any_name)

# class CustomRelatedDropdownFilter(RelatedDropdownFilter):
#     def choices(self, changelist):
#         yield {
#             'selected': self.lookup_val is None and not self.lookup_val_isnull,
#             'query_string': changelist.get_query_string(remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]),
#             'display': _('All'),
#         }
#         for pk_val, val in self.lookup_choices:
#             yield {
#                 'selected': self.lookup_val == str(pk_val),
#                 'query_string': changelist.get_query_string({self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]),
#                 'display': val,
#             }
  