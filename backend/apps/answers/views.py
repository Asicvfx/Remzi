from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.response import Response

from apps.answers.serializers import AskRequestSerializer, AskResponseSerializer
from apps.answers.services import AskQuestionService


@extend_schema(
    summary="Ask a question about your documents",
    description=(
        "Retrieves relevant chunks and returns an answer with citations. "
        "Uses OpenAI when configured, otherwise falls back to local extractive answers."
    ),
    request=AskRequestSerializer,
    responses={200: AskResponseSerializer},
)
class AskView(views.APIView):
    def post(self, request):
        serializer = AskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = AskQuestionService.execute(
            user=request.user,
            question=serializer.validated_data["question"],
            limit=serializer.validated_data["limit"],
            document_id=serializer.validated_data.get("document_id"),
        )
        response_serializer = AskResponseSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
