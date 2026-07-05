from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.response import Response

from apps.common.text import repair_mojibake
from apps.search.serializers import SearchRequestSerializer, SearchResponseSerializer
from apps.search.services import SearchChunksService


@extend_schema(
    summary="Search document chunks",
    description="Searches the authenticated user's document chunks with the local MVP embedding provider.",
    request=SearchRequestSerializer,
    responses={200: SearchResponseSerializer},
)
class SearchView(views.APIView):
    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]
        document_id = serializer.validated_data.get("document_id")
        results = SearchChunksService.execute(
            user=request.user,
            query=query,
            limit=limit,
            document_id=document_id,
        )

        payload = {
            "query": repair_mojibake(query),
            "document_id": document_id,
            "results": results,
        }
        response_serializer = SearchResponseSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
