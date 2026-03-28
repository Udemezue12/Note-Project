from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..webscokets.note_websocket_update import send_test_update


class TestWebSocket(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        send_test_update(
            test="testing_update", data={"message": "Hello from WebSocket 🚀"}
        )

        return Response({"status": "sent"})
