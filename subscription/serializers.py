from rest_framework import serializers

from subscription.models import SubscriptionPackage, PackageDescription


class PackageSerializer(serializers.ModelSerializer):
    '''
    Package Serializer
    '''
    class_error = None
    price = serializers.SerializerMethodField(read_only=True)
    plan_descriptions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubscriptionPackage
        fields = (
            'name', 'price', 'plan_descriptions', 'is_active', 'subscription_period'
        )

    def get_price(self, obj):
        _ = self.class_error
        
        plan_price = obj.price
        if obj.subscription_period == 3:
            plan_price = obj.price * 12
        return plan_price

    def get_plan_descriptions(self, obj):
        _ = self.class_error
        plan_descriptions = list(obj.plan_descriptions.all().values_list(
            'description', flat=True))
        return plan_descriptions
