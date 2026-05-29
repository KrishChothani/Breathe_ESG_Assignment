"""
apps/chatbot/serializers.py
===========================
DRF serializers for chatbot request validation and response shaping.
"""

import uuid
from rest_framework import serializers


class ChatQuerySerializer(serializers.Serializer):
    """Validates an incoming chatbot query request."""

    message = serializers.CharField(
        max_length=2000,
        help_text="The user's plain-English question.",
    )
    conversation_id = serializers.UUIDField(
        required=False,
        default=None,
        allow_null=True,
        help_text="UUID to continue a previous conversation thread. Omit to start a new one.",
    )
    context_row_id = serializers.UUIDField(
        required=False,
        default=None,
        allow_null=True,
        help_text="UUID of a specific emission row to explain (optional).",
    )
    context_row_source = serializers.ChoiceField(
        choices=['SAP', 'UTILITY', 'TRAVEL'],
        required=False,
        default=None,
        allow_null=True,
        help_text="Source table for context_row_id: SAP, UTILITY, or TRAVEL.",
    )

    def validate(self, data):
        """If context_row_id is provided, context_row_source must also be provided."""
        if data.get('context_row_id') and not data.get('context_row_source'):
            raise serializers.ValidationError(
                "context_row_source is required when context_row_id is provided."
            )
        return data


class ChartConfigSerializer(serializers.Serializer):
    """Shape of the chart_config field in the response."""

    type      = serializers.ChoiceField(choices=['line', 'bar', 'donut'])
    title     = serializers.CharField()
    x_key     = serializers.CharField()
    y_key     = serializers.CharField()
    color_key = serializers.CharField(allow_null=True, required=False)
    y_label   = serializers.CharField()
    x_label   = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    """Shapes the response body for POST /api/v1/chatbot/query/."""

    conversation_id      = serializers.UUIDField()
    message_id           = serializers.UUIDField()
    intent               = serializers.CharField(allow_null=True)
    answer               = serializers.CharField()
    response_type        = serializers.ChoiceField(choices=['text', 'table', 'chart', 'clarify'])
    table_data           = serializers.ListField(child=serializers.DictField(), allow_null=True)
    chart_config         = serializers.DictField(allow_null=True)
    chart_data           = serializers.ListField(child=serializers.DictField(), allow_null=True)
    suggested_follow_ups = serializers.ListField(child=serializers.CharField())
    execution_time_ms    = serializers.IntegerField()
    rows_returned        = serializers.IntegerField()
