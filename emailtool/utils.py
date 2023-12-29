
from import_export.widgets import ForeignKeyWidget
import csv

class ForeignKeyWidgetWithCreation(ForeignKeyWidget):

    def __init__(self, model, field="pk", create=False, **kwargs):
        self.model = model
        self.field = field
        self.create = create
        super(ForeignKeyWidgetWithCreation, self).__init__(model, field=field, **kwargs)
        
    def clean(self, value, **kwargs):
        if not value:
            return None
        if self.create:
            self.model.objects.get_or_create(**{self.field: value})

        # val = super(ForeignKeyWidgetWithCreation, self).clean(value, **kwargs)
        # val = super().clean(value)
        # if val:
        #     return self.get_queryset(value, row, *args, **kwargs).get(**{self.field: val})
        # else:
        #     return None
        return self.model.objects.filter(**{self.field: value}).order_by('modify_date').last() if value else None