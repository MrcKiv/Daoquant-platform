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

SAFE_STANDARD_LIBRARY_MODULES = (
    '__future__',
    'bisect',
    'collections',
    'copy',
    'dataclasses',
    'datetime',
    'decimal',
    'enum',
    'functools',
    'hashlib',
    'heapq',
    'itertools',
    'json',
    'logging',
    'math',
    'operator',
    'random',
    're',
    'statistics',
    'time',
    'traceback',
    'typing',
    'uuid',
    'warnings',
)

SAFE_THIRD_PARTY_MODULES = (
    'numpy',
    'pandas',
    'pymysql',
    'scipy',
    'sklearn',
    'sqlalchemy',
)

SAFE_DEEP_LEARNING_MODULES = (
    'torch',
)

SAFE_PROJECT_MODULE_PREFIXES = (
    'strategy',
)

RESTRICTED_MODULE_GROUPS = (
    {
        'title': '系统与文件能力',
        'modules': (
            'asyncio',
            'concurrent',
            'ctypes',
            'glob',
            'importlib',
            'multiprocessing',
            'os',
            'pathlib',
            'shutil',
            'subprocess',
            'sys',
            'tempfile',
            'threading',
        ),
    },
    {
        'title': '网络与外部数据',
        'modules': (
            'akshare',
            'baostock',
            'ftplib',
            'http',
            'requests',
            'socket',
            'smtplib',
            'telnetlib',
            'tushare',
            'urllib',
            'yfinance',
        ),
    },
    {
        'title': '不支持的机器学习与量化扩展',
        'modules': (
            'backtrader',
            'catboost',
            'cupy',
            'flax',
            'jax',
            'keras',
            'lightgbm',
            'numba',
            'talib',
            'tensorflow',
            'transformers',
            'xgboost',
        ),
    },
    {
        'title': '可视化与图像处理',
        'modules': (
            'cv2',
            'matplotlib',
            'PIL',
            'plotly',
            'seaborn',
        ),
    },
    {
        'title': '高风险序列化与缓存',
        'modules': (
            'dill',
            'joblib',
            'pickle',
            'redis',
            'shelve',
        ),
    },
)

RESTRICTED_MODULES = {
    module_name
    for group in RESTRICTED_MODULE_GROUPS
    for module_name in group['modules']
}

ALLOWED_TOP_LEVEL_MODULES = set(SAFE_STANDARD_LIBRARY_MODULES) | set(SAFE_THIRD_PARTY_MODULES) | set(
    SAFE_DEEP_LEARNING_MODULES
) | set(SAFE_PROJECT_MODULE_PREFIXES)


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


def _parse_strategy_ast(code_text):
    try:
        return ast.parse(code_text)
    except SyntaxError as exc:
        raise ValueError(f'Python 语法错误: 第 {exc.lineno} 行 {exc.msg}') from exc


def _module_matches(module_name, candidates):
    return any(
        module_name == candidate or module_name.startswith(f'{candidate}.')
        for candidate in candidates
    )


def _validate_import_policy(tree):
    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                violations.append(f'第 {node.lineno} 行使用了相对导入，当前仅支持绝对导入')
                continue
            imports = [(node.module, node.lineno)]
        else:
            continue

        for module_name, line_no in imports:
            if not module_name:
                continue

            root_module = module_name.split('.')[0]
            if _module_matches(module_name, RESTRICTED_MODULES):
                violations.append(f'第 {line_no} 行导入了受限库 `{module_name}`')
                continue

            if root_module not in ALLOWED_TOP_LEVEL_MODULES:
                violations.append(f'第 {line_no} 行导入了未开放库 `{module_name}`')

    if violations:
        details = '；'.join(violations[:6])
        if len(violations) > 6:
            details += f'；另有 {len(violations) - 6} 处导入不符合规则'

        allowed_modules = '、'.join(
            list(SAFE_THIRD_PARTY_MODULES) + list(SAFE_DEEP_LEARNING_MODULES)
        )
        raise ValueError(
            '策略文件使用了未开放或受限的 Python 库。'
            f'{details}。'
            f'当前仅开放标准库子集、{allowed_modules}，以及项目内模块 strategy.*'
        )


def _find_entry_function(tree):
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for candidate in ENTRY_FUNCTION_CANDIDATES:
        if candidate in function_names:
            return candidate

    raise ValueError(
        '上传的策略文件中未找到入口函数，请至少定义 '
        + ' / '.join(ENTRY_FUNCTION_CANDIDATES)
    )


def get_upload_strategy_policy():
    return {
        'entryFunctions': list(ENTRY_FUNCTION_CANDIDATES),
        'maxUploadSizeKb': MAX_UPLOAD_SIZE // 1024,
        'profiles': {
            'regular': {
                'key': 'regular',
                'title': '普通策略模板',
                'description': '适合规则策略、指标策略、因子打分策略和统计模型策略。',
                'downloadPath': '/downloads/daoquant_strategy_template.py',
                'downloadName': 'daoquant_strategy_template.py',
                'recommendedModules': list(SAFE_THIRD_PARTY_MODULES) + ['strategy.*'],
            },
            'deep_learning': {
                'key': 'deep_learning',
                'title': '深度学习策略模板',
                'description': '适合使用 PyTorch 做时序评分、特征提取和小型模型推理的策略。',
                'downloadPath': '/downloads/daoquant_deep_learning_strategy_template.py',
                'downloadName': 'daoquant_deep_learning_strategy_template.py',
                'recommendedModules': list(SAFE_DEEP_LEARNING_MODULES)
                + ['numpy', 'pandas', 'scipy', 'sklearn', 'strategy.*'],
            },
        },
        'allowed': {
            'standardLibrary': list(SAFE_STANDARD_LIBRARY_MODULES),
            'thirdParty': list(SAFE_THIRD_PARTY_MODULES),
            'deepLearningExtra': list(SAFE_DEEP_LEARNING_MODULES),
            'projectPrefixes': [f'{item}.*' for item in SAFE_PROJECT_MODULE_PREFIXES],
        },
        'restrictedGroups': [
            {
                'title': group['title'],
                'modules': list(group['modules']),
            }
            for group in RESTRICTED_MODULE_GROUPS
        ],
    }


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
    tree = _parse_strategy_ast(code_text)
    _validate_import_policy(tree)
    entry_function = _find_entry_function(tree)
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
