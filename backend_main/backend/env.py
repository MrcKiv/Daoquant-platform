import os
from urllib.parse import quote_plus


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    value = os.getenv(name)
    raw = default if value is None else value
    if isinstance(raw, (list, tuple)):
        return [item for item in raw if item]
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def get_database_config():
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "jdgp"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", "123456"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": os.getenv("DB_CHARSET", "utf8mb4"),
        },
    }


def get_pymysql_config(charset="utf8mb4", **overrides):
    config = get_database_config()
    pymysql_config = {
        "host": config["HOST"],
        "port": int(config["PORT"]),
        "user": config["USER"],
        "password": config["PASSWORD"],
        "database": config["NAME"],
        "charset": charset,
    }
    pymysql_config.update(overrides)
    return pymysql_config


def get_sqlalchemy_database_url(charset="utf8mb4"):
    config = get_database_config()
    user = quote_plus(config["USER"])
    password = quote_plus(config["PASSWORD"])
    host = config["HOST"]
    port = config["PORT"]
    name = quote_plus(config["NAME"])
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset={charset}"
