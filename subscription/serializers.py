from rest_framework import serializers

from subscription.models import SubscriptionPackage, PackageDescription


class PackageSerializer(serializers.ModelSerializer):
    '''
    Package Serializer
    '''
    class_error = None
    plan_descriptions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubscriptionPackage
        fields = (
            'name', 'price', 'plan_descriptions', 'is_active', 'subscription_period'
        )

    def get_plan_descriptions(self, obj):
        _ = self.class_error
        plan_descriptions = list(obj.plan_descriptions.all().values_list(
            'description', flat=True))
        return plan_descriptions
