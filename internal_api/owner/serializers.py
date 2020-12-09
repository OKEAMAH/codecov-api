import logging
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from codecov_auth.models import Owner
from codecov_auth.constants import PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS, CURRENTLY_OFFERED_PLANS

from services.billing import BillingService


log = logging.getLogger(__name__)

class OwnerSerializer(serializers.ModelSerializer):
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = (
            'avatar_url',
            'service',
            'username',
            'email',
            'stats',
            'ownerid',
            'integration_id',
        )

        read_only_fields = fields

    def get_stats(self, obj):
        if obj.cache and 'stats' in obj.cache:
            return obj.cache['stats']


class ProfileSerializer(OwnerSerializer):
    class Meta:
        model = Owner
        fields = OwnerSerializer.Meta.fields + ('private_access',)


class StripeLineItemSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.FloatField()
    currency = serializers.CharField()
    period = serializers.JSONField()


class StripeInvoiceSerializer(serializers.Serializer):
    number = serializers.CharField()
    status = serializers.CharField()
    created = serializers.IntegerField()
    period_start = serializers.IntegerField()
    period_end = serializers.IntegerField()
    due_date = serializers.IntegerField()
    customer_name = serializers.CharField()
    customer_address = serializers.CharField()
    currency = serializers.CharField()
    amount_paid = serializers.FloatField()
    amount_due = serializers.FloatField()
    amount_remaining = serializers.FloatField()
    total = serializers.FloatField()
    subtotal = serializers.FloatField()
    invoice_pdf = serializers.CharField()
    line_items = StripeLineItemSerializer(many=True, source="lines.data")


class StripeCardSerializer(serializers.Serializer):
    brand = serializers.CharField()
    exp_month = serializers.IntegerField()
    exp_year = serializers.IntegerField()
    last4 = serializers.CharField()


class StripePaymentMethodSerializer(serializers.Serializer):
    card = StripeCardSerializer(read_only=True)


class PlanSerializer(serializers.Serializer):
    marketing_name = serializers.CharField(read_only=True)
    value = serializers.CharField()
    billing_rate = serializers.CharField(read_only=True)
    base_unit_price = serializers.IntegerField(read_only=True)
    benefits = serializers.JSONField(read_only=True)
    quantity = serializers.IntegerField(required=False)

    def validate_value(self, value):
        if value not in CURRENTLY_OFFERED_PLANS:
            raise serializers.ValidationError(
                f"Invalid value for plan: {value}; "
                f"must be one of {CURRENTLY_OFFERED_PLANS.keys()}"
            )
        return value

    def validate(self, plan):
        owner = self.context["view"].owner

        # Validate quantity here because we need access to whole plan object
        if plan["value"] in PR_AUTHOR_PAID_USER_PLAN_REPRESENTATIONS:
            if "quantity" not in plan:
                raise serializers.ValidationError(f"Field 'quantity' required for updating to paid plans")
            if plan["quantity"] < 5:
                raise serializers.ValidationError(f"Quantity for paid plan must be greater than 5")
            if plan["quantity"] < len(owner.plan_activated_users or []):
                raise serializers.ValidationError(f"Quantity cannot be lower than currently activated user count")
        return plan


class SubscriptionDetailSerializer(serializers.Serializer):
    latest_invoice = StripeInvoiceSerializer()
    default_payment_method = StripePaymentMethodSerializer()
    cancel_at_period_end = serializers.BooleanField()
    current_period_end = serializers.IntegerField()
    customer = serializers.CharField()


class AccountDetailsSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(source="pretty_plan")
    checkout_session_id = serializers.SerializerMethodField()
    subscription_detail = serializers.SerializerMethodField()
    payment_method = serializers.CharField(write_only=True)

    class Meta:
        model = Owner
        fields = (
            'activated_user_count',
            'inactive_user_count',
            'plan_auto_activate',
            'integration_id',
            'plan',
            'subscription_detail',
            'checkout_session_id',
            'name',
            'email',
            'payment_method',
        )

    def _get_billing(self):
        current_user = self.context["request"].user
        return BillingService(requesting_user=current_user)

    def get_subscription_detail(self, owner):
        subscription_detail = self._get_billing().get_subscription(owner)
        if subscription_detail:
            return SubscriptionDetailSerializer(subscription_detail).data

    def get_checkout_session_id(self, _):
        return self.context.get("checkout_session_id")

    def update(self, instance, validated_data):
        if "payment_method" in validated_data:
            self._get_billing().update_payment_method(instance, validated_data.pop("payment_method"))

        if "pretty_plan" in validated_data:
            checkout_session_id_or_none = self._get_billing().update_plan(
                instance,
                validated_data.pop("pretty_plan")
            )

            if checkout_session_id_or_none is not None:
                self.context["checkout_session_id"] = checkout_session_id_or_none

        super().update(instance, validated_data)
        return self.context["view"].get_object()


class UserSerializer(serializers.ModelSerializer):
    activated = serializers.BooleanField()
    is_admin = serializers.BooleanField()
    latest_private_pr_date = serializers.DateTimeField()
    lastseen = serializers.DateTimeField()

    class Meta:
        model = Owner
        fields = (
            'activated',
            'is_admin',
            'username',
            'email',
            'ownerid',
            'student',
            'name',
            'latest_private_pr_date',
            'lastseen',
        )

    def update(self, instance, validated_data):
        owner = self.context["view"].owner

        if "activated" in validated_data:
            if validated_data["activated"] is True and owner.can_activate_user(instance):
                owner.activate_user(instance)
            elif validated_data["activated"] is False:
                owner.deactivate_user(instance)
            else:
                raise PermissionDenied(f"Cannot activate user {instance.username} -- not enough seats left.")

        if "is_admin" in validated_data:
            if validated_data["is_admin"]:
                owner.add_admin(instance)
            else:
                owner.remove_admin(instance)

        # Re-fetch from DB to set activated and admin fields
        return self.context["view"].get_object()
