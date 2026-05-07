
from datetime import timezone
from rest_framework import serializers
from tools.models import DataSourceItem, EmailData, DataSourceJob, DataSourceJob, ScraperResult
from tools.helper import EmailCheckHelper
from tools import constants
from celery.result import AsyncResult

class SingleValidationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super(SingleValidationSerializer, self).__init__(*args, **kwargs)
        context = kwargs.get('context', None)
        if context:
            self.request = kwargs['context']['request']

    def create(self, validated_data):
        email_helper = EmailCheckHelper(self.request)
        email = validated_data.get('email')
        result = email_helper.validate_email(email, action=constants.SINGLE)
        return result

class SingleValidationHistorySerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='input_value', read_only=True)
    result = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    domain = serializers.SerializerMethodField()
    role_based = serializers.SerializerMethodField()
    catch_all = serializers.SerializerMethodField()
    disposable = serializers.SerializerMethodField()

    create_date = serializers.SerializerMethodField()

    class Meta:
        model = DataSourceItem
        fields = (
            "email",
            "result",
            "status",
            "domain",
            "role_based",
            "catch_all",
            "disposable",
            "create_date",
        )

    def _rd(self, obj):
        """Shortcut to result_data"""
        return obj.result_data or {}

    def _nested(self, data, *keys, default=None):
        """Safe nested dict getter"""
        for key in keys:
            if not isinstance(data, dict):
                return default
            data = data.get(key)
        return default if data is None else data


    def get_result(self, obj):
        return self._rd(obj).get("email_result")

    def get_status(self, obj):
        status = self._rd(obj).get("status")
        if status is None:
            return None
        return EmailData.STATUS_DICT.get(status, status)

    def get_domain(self, obj):
        return self._rd(obj).get("has_domain_mx")

    def get_role_based(self, obj):
        return self._rd(obj).get("is_role_based")

    def get_catch_all(self, obj):
        return self._rd(obj).get("catch_all")
    
    def get_disposable(self, obj):
        return self._rd(obj).get("is_disposable")

    def get_create_date(self, obj):
        if obj.create_date:
            return obj.create_date.astimezone().strftime("%d/%m/%Y %H:%M")

    
class DataSourceJobSerializer(serializers.ModelSerializer):
    completed_at = serializers.SerializerMethodField()
    upload_completed_at = serializers.SerializerMethodField()

    class Meta(object):
        model = DataSourceJob
        fields = ('uuid', 'name','status','total_items','valid_count','source_format', 'total_duplicate',
                  'syntax_invalid_count','role_based_count','disposable_count','completed_count', 'risky_count',
                  'catch_all_count','invalid_count','unknown_count','status','upload_completed_at',
                  'started_at','completed_at')
        
    def get_completed_at(self, obj):
        _ = self.__class__.__name__
        if obj.completed_at:
            return obj.completed_at.astimezone().strftime("%d/%m/%Y %H:%M")
        

    def get_upload_completed_at(self, obj):
        _ = self.__class__.__name__
        if obj.upload_completed_at:
            return obj.upload_completed_at.astimezone().strftime("%d/%m/%Y %H:%M")
        
        

class BulkStatusRequestSerializer(serializers.Serializer):
    job_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )

class ScraperResultSerializer(serializers.ModelSerializer):
    create_date = serializers.SerializerMethodField()
    class Meta:
        model = ScraperResult
        fields = ('url','final_url','scrape_name','emaildata','scrapedata', 'create_date')

    
    def get_create_date(self, obj):
        _ = self.__class__.__name__
        if obj.create_date:
            return obj.create_date.astimezone().strftime("%d/%m/%Y %H:%M")

    
class ScraperJobSerializer(serializers.ModelSerializer):
    completed_at = serializers.SerializerMethodField()
    upload_completed_at = serializers.SerializerMethodField()

    class Meta(object):
        model = DataSourceJob
        fields = ('uuid', 'name','status','total_items','valid_count','source_format', 'total_duplicate',
                  'syntax_invalid_count','role_based_count','disposable_count','completed_count', 'risky_count',
                  'catch_all_count','invalid_count','unknown_count','status','upload_completed_at',
                  'started_at','completed_at')
        
    def get_completed_at(self, obj):
        _ = self.__class__.__name__
        if obj.completed_at:
            return obj.completed_at.astimezone().strftime("%d/%m/%Y %H:%M")
        

    def get_upload_completed_at(self, obj):
        _ = self.__class__.__name__
        if obj.upload_completed_at:
            return obj.upload_completed_at.astimezone().strftime("%d/%m/%Y %H:%M")