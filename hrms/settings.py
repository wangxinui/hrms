"""Django settings for hrms project."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-5sty^m6!icqet=idr8(&akb97t9rc!d52a)zev#ul7@*d3h*$1",
)

# ── 调试开关：环境变量 DEBUG=False 关闭，否则默认开启 ──────────────────────
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

# ── 允许的 Host（本地开发 + 常见答辩环境） ──────────────────────────────────────
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", ".local", ".lan"]

# ── 安全响应头（由 SecurityMiddleware 注入） ──────────────────────────────────
# 生产环境部署时务必打开 USE_X_FORWARDED_HOST / SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = 31536000          # 1 年 HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True      # 禁止浏览器 MIME 嗅探
SECURE_BROWSER_XSS_FILTER = True        # 启用浏览器内置 XSS 过滤
SECURE_REFERRER_POLICY = "same-origin"  # Referer 只在同源请求发送

# ── CSRF 与 Session Cookie ───────────────────────────────────────────────────
# 开发阶段只设 HttpOnly / SameSite；若走 HTTPS 再把两个 SESSION_COOKIE_* 设 True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 86400              # Session 24 小时过期
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True       # 每次请求刷新过期时间

# ── X-Frame-Options ──────────────────────────────────────────────────────────
# XFrameOptionsMiddleware 已在 MIDDLEWARE 里，默认 SAMEORIGIN
X_FRAME_OPTIONS = "SAMEORIGIN"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "app01",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "app01.middleware.auth.AuthMiddleware",
]

ROOT_URLCONF = "hrms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "app01.context_processors.nav_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "hrms.wsgi.application"

import sys

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "hrms",
        "USER": "root",
        "PASSWORD": "root123",
        "HOST": "localhost",
        "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# ── 测试命令自动切 SQLite 内存库，不依赖 MySQL ──────────────────────────────
if "test" in sys.argv or "pytest" in sys.modules:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "app01.User"

LOGIN_URL = "/login/"

# ── 分级日志配置 ──────────────────────────────────────────────────────────────
# DEBUG=True 时 INFO 及以上同时输出到控制台和文件
# 分级：DEBUG(开发细节) / INFO(业务关键节点) / WARNING(异常但可恢复) / ERROR(需排查) / CRITICAL(系统级)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "info.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "error.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "file_security": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "security.log",
            "maxBytes": 3 * 1024 * 1024,
            "backupCount": 2,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        # 业务代码日志
        "app01": {
            "level": "INFO",
            "handlers": ["console", "file_info", "file_error"],
            "propagate": False,
        },
        # Django 请求日志
        "django.request": {
            "level": "ERROR",
            "handlers": ["file_error"],
            "propagate": False,
        },
        # Django 安全相关（CSRF/403 等）
        "django.security": {
            "level": "WARNING",
            "handlers": ["file_security"],
            "propagate": False,
        },
        # 数据库慢查询（DEBUG=True 时启用）
        "django.db.backends": {
            "level": "WARNING",
            "handlers": ["console"],
            "filters": ["require_debug_true"],
            "propagate": False,
        },
    },
}
