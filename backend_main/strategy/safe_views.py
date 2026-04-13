import json
import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import User_Strategy_Configuration
from .report_cache import delete_backtest_cache
import strategy.mysql_connect as sc


def serialize_json_field(value):
    if value in (None, ""):
        return None
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def get_strategy_config_queryset(user_id, strategy_name):
    return User_Strategy_Configuration.objects.filter(
        userID=str(user_id),
        strategyName=strategy_name,
    ).order_by('-id')


def get_latest_strategy_config(user_id, strategy_name):
    queryset = get_strategy_config_queryset(user_id, strategy_name)
    strategy_config = queryset.first()
    duplicate_count = queryset.count()
    if strategy_config and duplicate_count > 1:
        print(
            f"Warning: found {duplicate_count} strategy configs for "
            f"user={user_id}, strategy={strategy_name}. Using latest id={strategy_config.id}."
        )
    return strategy_config


def upsert_strategy_config(user_id, strategy_name, defaults):
    queryset = get_strategy_config_queryset(user_id, strategy_name)
    strategy_config = queryset.first()
    duplicate_count = queryset.count()

    if strategy_config:
        queryset.update(**defaults)
        strategy_config.refresh_from_db()
        if duplicate_count > 1:
            print(
                f"Warning: updated {duplicate_count} duplicate strategy configs for "
                f"user={user_id}, strategy={strategy_name}."
            )
        return strategy_config, False

    strategy_config = User_Strategy_Configuration.objects.create(
        userID=str(user_id),
        strategyName=strategy_name,
        **defaults,
    )
    return strategy_config, True


@csrf_exempt
def get_strategy_config(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Only POST is supported."}, status=405)

    try:
        data = json.loads(request.body)
        strategy_name = data.get('strategyName')
        user_id = request.session.get('user_id')
        print("strategy_name:", strategy_name)
        print("user_id:", user_id)

        if not strategy_name or not user_id:
            return JsonResponse({'success': False, 'message': 'Missing strategyName or userID.'}, status=400)

        defaults = {
            'init_fund': data.get('capital'),
            'max_hold_num': data.get('hold'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'income_base': data.get('benchmark'),
            'labels': serialize_json_field(data.get('labels')),
            'source_user_id': user_id,
        }
        _, created = upsert_strategy_config(user_id, strategy_name, defaults)

        return JsonResponse({
            "success": True,
            "message": "Strategy config created." if created else "Strategy config updated.",
            "received_data": data,
        }, status=200)
    except Exception as e:
        print(f"get_strategy_config error: {e}")
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def get_stock_selector(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Only POST is supported."}, status=405)

    try:
        data = json.loads(request.body)
        strategy_name = data.get('strategyName')
        user_id = request.session.get('user_id')

        if not strategy_name or not user_id:
            return JsonResponse({'success': False, 'message': 'Missing strategyName or userID.'}, status=400)

        defaults = {
            'optionfactor': serialize_json_field(data.get('conditions')),
        }
        upsert_strategy_config(user_id, strategy_name, defaults)
        return JsonResponse({"success": True, "received_data": data}, status=200)
    except Exception as e:
        print(f"get_stock_selector error: {e}")
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def get_factor_config(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Only POST is supported."}, status=405)

    try:
        data = json.loads(request.body)
        strategy_name = data.get('strategyName')
        user_id = request.session.get('user_id')
        print("strategy_name:", strategy_name)
        print("user_id:", user_id)

        if not strategy_name or not user_id:
            return JsonResponse({'success': False, 'message': 'Missing strategyName or userID.'}, status=400)

        defaults = {
            'bottomfactor': serialize_json_field(data.get('factors')),
        }
        upsert_strategy_config(user_id, strategy_name, defaults)
        return JsonResponse({"success": True, "received_data": data}, status=200)
    except Exception as e:
        print(f"get_factor_config error: {e}")
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
def public_strategy(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Only POST is supported."}, status=405)

    try:
        data = json.loads(request.body)
        strategy_name = data.get('strategyName')
        user_id = request.session.get('user_id')

        if not strategy_name or not user_id:
            return JsonResponse({'success': False, 'message': 'Missing strategyName or userID.'}, status=400)

        strategy_config = get_latest_strategy_config(user_id, strategy_name)
        if not strategy_config:
            return JsonResponse({'success': False, 'message': 'Strategy config not found.'}, status=404)

        strategy_config.is_public = True
        strategy_config.source_user_id = user_id
        strategy_config.save()
        return JsonResponse({"success": True, "message": "Strategy published."}, status=200)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
def insert_name(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST is supported.'}, status=405)

    try:
        data = json.loads(request.body)
        strategy_name = data.get('strategyName')
        if not strategy_name:
            return JsonResponse({'success': False, 'message': 'Strategy name is required.'}, status=400)

        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'Not logged in.'}, status=401)

        if get_latest_strategy_config(user_id, strategy_name):
            return JsonResponse({'success': False, 'message': 'Strategy name already exists.'}, status=400)

        User_Strategy_Configuration.objects.create(
            strategyName=strategy_name,
            userID=str(user_id),
        )
        return JsonResponse({'success': True, 'message': 'Strategy created.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
def delete_strategy(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST is supported.'}, status=405)

    try:
        data = json.loads(request.body)
        user_id = request.session.get('user_id')
        strategy_name = data.get('strategyName')

        if not strategy_name:
            return JsonResponse({'success': False, 'message': 'Missing strategyName.'}, status=400)

        queryset = User_Strategy_Configuration.objects.filter(
            userID=user_id,
            strategyName=strategy_name,
        )
        strategy_config = queryset.first()
        if strategy_config:
            sid = strategy_config.id
            sc.execute_sql(f"DELETE FROM {sc.table_shareholding} WHERE strategy_id=%s AND user_id=%s", (sid, user_id))
            sc.execute_sql(f"DELETE FROM {sc.table_transaction} WHERE strategy_id=%s AND user_id=%s", (sid, user_id))
            sc.execute_sql(f"DELETE FROM {sc.table_statistic} WHERE strategy_id=%s AND user_id=%s", (sid, user_id))
            sc.execute_sql(f"DELETE FROM {sc.table_baseline} WHERE strategy_id=%s AND user_id=%s", (sid, user_id))
            delete_backtest_cache(user_id, strategy_name)
        deleted_count, _ = queryset.delete()
        if deleted_count == 0:
            return JsonResponse({'success': False, 'message': 'Strategy not found.'}, status=404)

        return JsonResponse({'success': True, 'message': 'Strategy deleted.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
