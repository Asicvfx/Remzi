from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)
    document_id = serializers.IntegerField(required=False, min_value=1)


class SearchResultSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    chunk_id = serializers.IntegerField()
    chunk_index = serializers.IntegerField()
    score = serializers.FloatField()
    text = serializers.CharField()


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    document_id = serializers.IntegerField(required=False, allow_null=True)
    results = SearchResultSerializer(many=True)
