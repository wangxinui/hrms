"""认证中间件 - 拦截未登录请求."""
from django.shortcuts import redirect
from django.conf import settings


# 无需登录的路径白名单
WHITE_LIST = [
    "/login/",
    "/captcha/",
    "/logout/",
    "/static/",
    "/media/",
    "/admin/",
    "/favicon.ico",
]


class AuthMiddleware:
    """登录拦截中间件."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 白名单直接放行
        for w in WHITE_LIST:
            if path.startswith(w):
                return self.get_response(request)

        # 已登录放行
        if request.user.is_authenticated:
            return self.get_response(request)

        # 未登录 -> 重定向
        login_url = settings.LOGIN_URL
        if request.method == "GET":
            return redirect(f"{login_url}?next={path}")
        return redirect(login_url)
