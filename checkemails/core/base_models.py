from django.conf import settings
from django.db import models, router
from django.db.models import Q
from django.db.models.deletion import (Collector,
                                       get_candidate_relations_to_delete)
from django.utils import timezone
from django.contrib.admin.utils import NestedObjects


class CheckEmailsBaseManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.with_deleted = kwargs.pop('deleted', False)
        super(CheckEmailsBaseManager, self).__init__(*args, **kwargs)

    def _base_queryset(self):
        _ = self
        return super().get_queryset()

    def get_queryset(self):
        qs = self._base_queryset()
        if self.with_deleted:
            return qs
        return qs.filter(is_deleted=False)


class CheckEmailsManager(CheckEmailsBaseManager):
    
    def get_queryset(self):
        qs = self._base_queryset()
        from app.middleware import get_current_user
        
        if self.with_deleted:
            return qs
        return qs.filter(is_deleted=False)


class CheckEmailsBaseWithDeleteModel(models.Model):
    '''
    Base model with hard delete
    '''
    create_date = models.DateTimeField(verbose_name='Create Date', default=timezone.now)
    modify_date = models.DateTimeField(verbose_name='Modify Date', auto_now=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Added By',
        on_delete=models.SET_NULL, blank=True, null=True, 
        related_name = 'added_%(class)ss_by')
    is_deleted = models.BooleanField(
        verbose_name='Is Deleted', default=False)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Modified By', 
        on_delete=models.SET_NULL, blank=True, null=True, 
        related_name = 'updated_%(class)ss_by')

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        from app.middleware import get_current_user
        current_user = get_current_user()
        return super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class CheckEmailsBaseModel(CheckEmailsBaseWithDeleteModel):
    '''
    Base Model with soft delete for all models in the project
    '''

    objects = CheckEmailsManager()
    objects_with_deleted = CheckEmailsManager(deleted=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self.pk is not None, (
            "%s object can't be deleted because its %s attribute is set to None." %
            (self._meta.object_name, self._meta.pk.attname)
        )
        collector = NestedObjects(using=using)
        collector.collect([self], keep_parents=keep_parents)
        objects_to_soft_delete = dict(collector.data)
        for _queryset in objects_to_soft_delete.values():
            if _queryset and hasattr(list(_queryset)[0], 'is_deleted'):
                for instance in _queryset:
                    instance.is_deleted = True
                    instance.save()
            else:
                for instance in _queryset:
                    instance.delete()
        self.is_deleted = True
        self.save()
        return None
