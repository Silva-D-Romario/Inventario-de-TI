from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(_request: object) -> JsonResponse:
    return JsonResponse(
        {
            "application": "Inventário de TI",
            "version": "0.6.0",
            "status": "UP",
        }
    )
