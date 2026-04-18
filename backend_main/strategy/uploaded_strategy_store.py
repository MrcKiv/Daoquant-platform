import ast
import importlib.util
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from django.conf import settings


ENTRY_FUNCTION_CANDIDATES = (
    'strategy_main',
    'my_strategy_main',
    'main',
    'run',
)
MAX_UPLOAD_SIZE = 512 * 1024


def _get_upload_base_dir():
    configured_dir = os.getenv('USER_STRATEGY_UPLOAD_DIR')
    if configured_dir:
        return Path(configured_dir)
    return settings.BASE_DIR / 'runtime_uploads' / 'user_strategies'


def _ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def _get_user_dir(user_id):
    user_dir = _get_upload_base_dir() / str(user_id)
    _ensure_dir(user_dir)
    return user_dir


def _normalize_strategy_id(name):
    cleaned = re.sub(r'[^0-9A-Za-z_\-\u4e00-\u9fff]+', '_', name or '').strip('._-')
    return cleaned[:80] or 'strategy'


def _metadata_path(user_id, strategy_id):
    return _get_user_dir(user_id) / f'{strategy_id}.json'


def _code_path(user_id, strategy_id):
    return _get_user_dir(user_id) / f'{strategy_id}.py'


def _read_metadata(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def _write_metadata(path, payload):
    temp_path = path.with_suffix('.json.tmp')
    with open(temp_path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def _find_entry_function(code_text):
    try:
        tree = ast.parse(code_text)
    except SyntaxError as exc:
        raise ValueError(f'Python 语法错误: 第 {exc.lineno} 行 {exc.msg}') from exc

    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for candidate in ENTRY_FUNCTION_CANDIDATES:
        if candidate in function_names:
            return candidate

    raise ValueError(
        '上传的策略文件中未找到入口函数，请至少定义 '
        + ' / '.join(ENTRY_FUNCTION_CANDIDATES)
    )


def list_uploaded_strategies(user_id):
    user_dir = _get_user_dir(user_id)
    strategies = []
    for metadata_file in user_dir.glob('*.json'):
        try:
            metadata = _read_metadata(metadata_file)
        except Exception:
            continue

        code_file = _code_path(user_id, metadata.get('id'))
        if not code_file.exists():
            continue

        strategies.append({
            'id': metadata.get('id'),
            'name': metadata.get('name'),
            'fileName': metadata.get('file_name'),
            'entryFunction': metadata.get('entry_function'),
            'updatedAt': metadata.get('updated_at'),
        })

    strategies.sort(key=lambda item: item.get('updatedAt') or '', reverse=True)
    return strategies


def save_uploaded_strategy(user_id, uploaded_file):
    if not uploaded_file:
        raise ValueError('未接收到策略文件')

    if not uploaded_file.name.lower().endswith('.py'):
        raise ValueError('只支持上传 .py 策略文件')

    if getattr(uploaded_file, 'size', 0) > MAX_UPLOAD_SIZE:
        raise ValueError('策略文件过大，请控制在 512KB 以内')

    raw_content = uploaded_file.read()
    try:
        code_text = raw_content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('策略文件需使用 UTF-8 编码') from exc

    display_name = Path(uploaded_file.name).stem.strip() or '未命名策略'
    strategy_id = _normalize_strategy_id(display_name)
    entry_function = _find_entry_function(code_text)
    updated_at = datetime.now().isoformat(timespec='seconds')

    code_file = _code_path(user_id, strategy_id)
    metadata_file = _metadata_path(user_id, strategy_id)
    existed = code_file.exists() or metadata_file.exists()

    with open(code_file, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(code_text)

    metadata = {
        'id': strategy_id,
        'name': display_name,
        'file_name': uploaded_file.name,
        'entry_function': entry_function,
        'updated_at': updated_at,
    }
    _write_metadata(metadata_file, metadata)

    return {
        'id': strategy_id,
        'name': display_name,
        'fileName': uploaded_file.name,
        'entryFunction': entry_function,
        'updatedAt': updated_at,
    }, existed


def load_uploaded_strategy_callable(user_id, strategy_id):
    metadata_file = _metadata_path(user_id, strategy_id)
    code_file = _code_path(user_id, strategy_id)
    if not metadata_file.exists() or not code_file.exists():
        raise FileNotFoundError('未找到上传策略文件')

    metadata = _read_metadata(metadata_file)
    entry_function = metadata.get('entry_function')
    module_name = f"uploaded_strategy_{user_id}_{strategy_id}_{int(code_file.stat().st_mtime)}"

    spec = importlib.util.spec_from_file_location(module_name, code_file)
    if not spec or not spec.loader:
        raise ValueError('无法加载上传策略模块')

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    strategy_callable = getattr(module, entry_function, None)
    if not callable(strategy_callable):
        raise ValueError(f'上传策略入口函数不可调用: {entry_function}')

    return metadata, strategy_callable
