from rest_framework import serializers


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    limit = serializers.IntegerField(default=5, min_value=1, max_value=10)
    document_id = serializers.IntegerField(required=False, min_value=1)


class AnswerCitationSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    chunk_id = serializers.IntegerField()
    chunk_index = serializers.IntegerField()
    score = serializers.FloatField()
    text = serializers.CharField()


class AskResponseSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()
    answer_mode = serializers.ChoiceField(choices=("local", "openai"))
    model = serializers.CharField(allow_blank=True)
    document_id = serializers.IntegerField(required=False, allow_null=True)
    citations = AnswerCitationSerializer(many=True)
