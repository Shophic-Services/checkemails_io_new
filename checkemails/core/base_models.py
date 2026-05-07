from django.conf import settings
from django.db import models, router
from django.db.models import Q
from itertools import chain
from django.db.models.deletion import (Collector,
                                       get_candidate_relations_to_delete)
from django.utils import timezone
from django.contrib.admin.utils import NestedObjects
from django.db.models.sql.constants import CURSOR
from django.db import (
    transaction,
)
from checkemails.core.exceptions import is_redis_available


class CheckEmailsQuerySet(models.query.QuerySet):
    def update(self, *args, **kwargs):
        """
        Update all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        self._not_support_combined_queries('update')
        assert not self.query.is_sliced, \
            "Cannot update a query once a slice has been taken."
        self._for_write = True
        query = self.query.chain(models.sql.UpdateQuery)
        query.add_update_values(kwargs)
        # Clear any annotations so that they won't be present in subqueries.
        query.annotations = {}
        with transaction.mark_for_rollback_on_error(using=self.db):
            objects = list(self)
            try:
                query.add_update_values({'modify_date':timezone.now()})
                rows = query.get_compiler(self.db).execute_sql(CURSOR)
            except Exception:
                rows = query.get_compiler(self.db).execute_sql(CURSOR)
            pks = {obj.pk for obj in objects}
            new_objects = self.model.objects.filter(pk__in=pks).using(self.db)
        self._result_cache = None
        if is_redis_available() and not self._for_write:  
            from cacheops import invalidate_obj 
            for obj in chain(objects, new_objects):
                invalidate_obj(obj, using=self.db)
        return rows
    

class CheckEmailsBaseManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.with_deleted = kwargs.pop('deleted', False)
        self.with_belongs = kwargs.pop('belongs', False)
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
        from core.middleware import get_current_user, get_belongs_user
        if get_current_user() and  get_current_user().is_authenticated and self.with_belongs:
            
            qs = qs.filter(Q(belongs_to=get_belongs_user(get_current_user())) |
                                    Q(belongs_to__isnull=True))
        
        if self.with_deleted:
            return qs
        return qs.filter(is_deleted=False)



class ModelDiffMixin(object):
    """
    A model mixin that tracks model fields' values and provide some useful api
    to know what fields have been changed.
    """

    def __init__(self, *args, **kwargs):
        super(ModelDiffMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def diff(self):
        d1 = self.__initial
        d2 = self._dict
        diffs = [(v, {'previous':v, 'updated':d2[k]}) for k, v in d1.items() if v != d2[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, None)

    def save(self, *args, **kwargs):
        """
        Saves model and set initial state.
        """
        super(ModelDiffMixin, self).save(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        fields_set = []
        dataset = []
        from checkemails.core.model_fields import ImageField, DocumentField, VideoDocumentField
        for field in self._meta.fields:
            if field.__class__ in [models.FileField, models.ImageField,ImageField, DocumentField, VideoDocumentField ]:
                fields_set.append(field.name)
                dataset.append(field)
        data = {}
        for f in dataset:
            if not getattr(f, 'editable', False):
                continue
            if fields_set and f.name not in fields_set:
                continue
            data[f.name] = f.value_from_object(self)
        return data


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
    belongs_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Belongs To', 
        on_delete=models.SET_NULL, blank=True, null=True, 
        related_name = 'belongs_%(class)ss_to')

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        from core.middleware import get_belongs_user, get_current_user
        current_user = get_current_user()
        if current_user and current_user.is_authenticated and not self.belongs_to:
            self.belongs_to = get_belongs_user(current_user)
        if current_user and current_user.is_authenticated and not self.added_by:
            self.added_by = current_user
        return super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class CheckEmailsBaseModel(CheckEmailsBaseWithDeleteModel):
    '''
    Base Model with soft delete for all models in the project
    '''
    without_user = CheckEmailsManager(belongs=True)
    without_user_with_deleted = CheckEmailsManager(deleted=False, belongs=True)
    objects = CheckEmailsManager(belongs=True)
    objects_with_deleted = CheckEmailsManager(deleted=True, belongs=True)

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
        self.soft_delete = True
        for _queryset in objects_to_soft_delete.values():
            if _queryset and hasattr(list(_queryset)[0], 'is_deleted'):
                for instance in _queryset:
                    instance.is_deleted = True
                    instance.save()
                self.soft_delete = False
                    
        if self.soft_delete:
            return collector.delete()
        self.save()
        return None


class CheckEmailsModelWithoutUser(CheckEmailsBaseWithDeleteModel):
    '''
    Base Model with soft delete for all models in the project
    '''

    objects = CheckEmailsBaseManager()
    objects_with_deleted = CheckEmailsBaseManager(deleted=True)

    
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
        self.soft_delete = True
        for _queryset in objects_to_soft_delete.values():
            if _queryset and hasattr(list(_queryset)[0], 'is_deleted'):
                for instance in _queryset:
                    instance.is_deleted = True
                    instance.save()
                self.soft_delete = False
                    
        if self.soft_delete:
            return collector.delete()
        self.save()
        return None