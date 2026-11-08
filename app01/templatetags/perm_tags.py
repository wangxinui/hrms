"""模板权限标签."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def can(context, code):
    """在模板中判断当前用户是否拥有指定权限编码.

    用法：{% can 'employee_add' as can_add %}{% if can_add %}...{% endif %}
    """
    has_perm = context.get("has_perm")
    return bool(has_perm and has_perm(code))
