"""模板上下文处理器 - 注入导航权限等."""
from .models import DEFAULT_PASSWORD
from .scoping import ROLE_EMP, role_code

# 普通员工视角下菜单的业务语义改名
EMP_LABELS = {
    "员工管理": "我的档案",
    "考勤管理": "我的考勤",
    "薪资管理": "我的薪资",
    "任务管理": "我的任务",
    "公告管理": "公告通知",
}


def nav_processor(request):
    """注入侧边栏菜单和权限."""
    user = request.user
    nav_items = [
        {"name": "工作台", "icon": "fa-dashboard", "url": "/", "perm": None},
        {"name": "部门管理", "icon": "fa-sitemap", "url": "/depart/", "perm": "department_view"},
        {"name": "员工管理", "icon": "fa-users", "url": "/employee/", "perm": "employee_view"},
        {"name": "考勤管理", "icon": "fa-clock-o", "url": "/attendance/", "perm": "attendance_view"},
        {"name": "薪资管理", "icon": "fa-money", "url": "/salary/", "perm": "salary_view"},
        {"name": "公告管理", "icon": "fa-bullhorn", "url": "/announcement/", "perm": "announcement_view"},
        {"name": "任务管理", "icon": "fa-tasks", "url": "/task/", "perm": "task_view"},
        {"name": "数据统计", "icon": "fa-bar-chart", "url": "/stats/", "perm": "stats_view"},
    ]

    permissions = set()
    if user.is_authenticated and user.role_id:
        permissions = set(
            user.role.permissions.values_list("code", flat=True)
        )

    current_role = role_code(user)

    def has_perm(code):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return code in permissions

    if current_role == ROLE_EMP:
        for item in nav_items:
            item["name"] = EMP_LABELS.get(item["name"], item["name"])

    visible_nav = [n for n in nav_items if n["perm"] is None or has_perm(n["perm"])]

    return {
        "nav_items": visible_nav,
        "permissions": permissions,
        "has_perm": has_perm,
        "role_code": current_role,
        "role_label": user.role.name if user.is_authenticated and user.role_id else "",
        "default_password": DEFAULT_PASSWORD,
    }
