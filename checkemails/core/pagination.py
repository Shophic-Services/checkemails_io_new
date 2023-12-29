
from django.utils.functional import cached_property
from django.conf import settings
from collections import OrderedDict
import inspect
from django.utils.inspect import method_has_no_args

from django.core.paginator import Paginator


class CustomPaginator(Paginator):
    @cached_property
    def count(self):
        """Return the total number of objects, across all pages."""
        return self.object_list.count()


from django.contrib.admin.views.main import ChangeList

class InlineChangeList(object):
    can_show_all = True
    multi_page = True
    get_query_string = ChangeList.__dict__['get_query_string']

    def __init__(self, request, page_num, paginator):
        self.show_all = 'all' in request.GET
        self.page_num = page_num
        self.paginator = paginator
        self.result_count = paginator.count
        self.params = dict(request.GET.items())