from django.urls import reverse
from django.contrib.admin import widgets
from django.template.loader import get_template
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter
from django.contrib.auth.forms import ReadOnlyPasswordHashWidget
from django.utils.translation import gettext_lazy as _

class DownloadFileWidget(widgets.AdminFileWidget):
    id = None
    template_name = 'admin/widgets/download_file_input.html'

    def __init__(self, id, attrs=None):
        self.id = id
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['download_url'] = reverse('app:attachment', kwargs={'pk': self.id})
        return context

class CustomReadOnlyPasswordHashWidget(ReadOnlyPasswordHashWidget):
    template_name = 'admin/widgets/read_only_password_hash.html'

class CustomRelatedDropdownFilter(RelatedDropdownFilter):
    def choices(self, changelist):
        yield {
            'selected': self.lookup_val is None and not self.lookup_val_isnull,
            'query_string': changelist.get_query_string(remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]),
            'display': _('All'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_val == str(pk_val),
                'query_string': changelist.get_query_string({self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]),
                'display': val,
            }