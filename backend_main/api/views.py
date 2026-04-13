from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections


def hello_world(request):
    return JsonResponse({"message": "Hello from Django backend!"})


def health_check(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception as exc:
        return JsonResponse({"status": "error", "database": str(exc)}, status=503)
