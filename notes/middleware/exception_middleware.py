import logging

from django.conf import settings
from django.http import JsonResponse

from ..friendly_msg import get_friendly_message

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)

        except Exception as exception:
            trace_id = request.headers.get("X-Request-ID", "none")
            client_ip = request.META.get("REMOTE_ADDR", "unknown")

          
            logger.error(
                f"[GLOBAL ERROR] TraceID={trace_id} | "
                f"Path={request.path} | "
                f"Method={request.method} | "
                f"Client={client_ip} | "
                f"Error={exception}",
                exc_info=True,
            )

          
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {
                        "detail": get_friendly_message(exception),
                        "trace_id": trace_id,  
                    },
                    status=500,
                )

            if settings.DEBUG:
                raise

            return JsonResponse(
                {"detail": "Something went wrong"},
                status=500,
            )
