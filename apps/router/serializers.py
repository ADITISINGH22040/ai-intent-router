from rest_framework import serializers

MAX_QUERY_LENGTH = 2000


class QueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=MAX_QUERY_LENGTH,
        trim_whitespace=True,
        error_messages={
            "blank": "Query must not be empty.",
            "required": "Query is required.",
            "max_length": f"Query must be at most {MAX_QUERY_LENGTH} characters.",
        },
    )

    def validate_query(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Query must not be empty.")
        return value
