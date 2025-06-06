from functools import wraps
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# This decorator checks for the presence of an API key in the request headers.
def require_api_key(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get("x-api-key")
        expected_key = getattr(settings, "KIOSK_API_KEY", None)
        if api_key != expected_key:
            logger.warning("Unauthorized access attempt with invalid API key.")
            return JsonResponse({"error": "Unauthorized - Invalid API key"}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view