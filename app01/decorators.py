"""权限装饰器 - 视图级 RBAC 校验."""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


def perm_required(perm_code, login_url="/login/"):
    """视图级权限校验装饰器.

    超级管理员直接放行；其余角色按 Role -> Permission 的多对多关系判断。
    AJAX 请求返回 JSON 错误，普通请求提示后跳回工作台。
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(f"{login_url}?next={request.path}")
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            if user.role_id and user.role.permissions.filter(code=perm_code).exists():
                return view_func(request, *args, **kwargs)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"code": 403, "msg": "您没有权限执行该操作"}, status=403)
            messages.error(request, "您没有权限访问该页面")
            return redirect("/")
        return wrapper
    return decorator
