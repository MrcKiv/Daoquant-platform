from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections

from api.stock_backfill import get_stock_backfill_status, start_stock_backfill
from user.decorators import permission_required

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


@permission_required('admin')
def stock_backfill_status(request):
    if request.method != 'GET':
        return JsonResponse({"error": "只支持 GET 请求"}, status=405)
    return JsonResponse(get_stock_backfill_status())


@permission_required('admin')
def stock_backfill_start(request):
    if request.method != 'POST':
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    started, state, status_code = start_stock_backfill()
    return JsonResponse(
        {
            "success": started,
            "message": "补数任务已启动" if started else state.get("message") or "补数任务启动失败",
            "state": state,
        },
        status=status_code,
    )
