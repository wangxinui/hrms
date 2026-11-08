"""自定义模板标签 - 权限检查."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def check_perm(context, perm_code):
    """在模板中检查当前用户是否有某权限.

    用法: {% check_perm 'department_add' as can_add %}
    """
    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    user = request.user
    if user.role_id:
        return user.role.permissions.filter(code=perm_code).exists()
    return True  # 未配置角色时默认放行


@register.simple_tag
def level_badge(level):
    """返回任务级别对应的 Bootstrap label class."""
    mapping = {1: "label-danger", 2: "label-warning", 3: "label-info", 4: "label-default"}
    return mapping.get(int(level), "label-default")


@register.simple_tag
def status_badge(status, kind="attendance"):
    """返回状态对应的 label class."""
    if kind == "attendance":
        mapping = {
            "normal": "label-success", "late": "label-warning",
            "early": "label-warning", "absent": "label-danger",
        }
    elif kind == "task":
        mapping = {
            "todo": "label-default", "doing": "label-info", "done": "label-success",
        }
    else:
        mapping = {}
    return mapping.get(status, "label-default")
