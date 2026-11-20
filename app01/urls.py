"""app01 URL 路由."""
from django.urls import path
from . import (
    auth_views, dashboard,
    department_views, employee_views, attendance_views,
    salary_views, announcement_views, task_views, stats_views,
    ai_views,
)

urlpatterns = [
    # 认证
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("captcha/", auth_views.captcha_view, name="captcha"),
    path("password/change/", auth_views.password_change, name="password_change"),

    # 首页
    path("", dashboard.dashboard, name="dashboard"),

    # 部门
    path("depart/", department_views.dept_list, name="dept_list"),
    path("depart/add/", department_views.dept_add, name="dept_add"),
    path("depart/<int:pk>/edit/", department_views.dept_edit, name="dept_edit"),
    path("depart/<int:pk>/delete/", department_views.dept_delete, name="dept_delete"),

    # 员工
    path("employee/", employee_views.emp_list, name="emp_list"),
    path("employee/add/", employee_views.emp_add, name="emp_add"),
    path("employee/<int:pk>/fragment/", employee_views.emp_detail_fragment,
         name="emp_detail_fragment"),
    path("employee/<int:pk>/edit/", employee_views.emp_edit, name="emp_edit"),
    path("employee/<int:pk>/delete/", employee_views.emp_delete, name="emp_delete"),
    path("employee/<int:pk>/", employee_views.emp_detail, name="emp_detail"),
    path("employee/<int:pk>/reset-password/", employee_views.emp_reset_password,
         name="emp_reset_password"),

    # 考勤
    path("attendance/", attendance_views.att_list, name="att_list"),
    path("attendance/add/", attendance_views.att_add, name="att_add"),
    path("attendance/<int:pk>/edit/", attendance_views.att_edit, name="att_edit"),
    path("attendance/<int:pk>/delete/", attendance_views.att_delete, name="att_delete"),

    # 薪资
    path("salary/", salary_views.sal_list, name="sal_list"),
    path("salary/add/", salary_views.sal_add, name="sal_add"),
    path("salary/<int:pk>/edit/", salary_views.sal_edit, name="sal_edit"),
    path("salary/<int:pk>/delete/", salary_views.sal_delete, name="sal_delete"),

    # 公告
    path("announcement/", announcement_views.ann_list, name="ann_list"),
    path("announcement/add/", announcement_views.ann_add, name="ann_add"),
    path("announcement/<int:pk>/edit/", announcement_views.ann_edit, name="ann_edit"),
    path("announcement/<int:pk>/top/", announcement_views.ann_toggle_top, name="ann_toggle_top"),
    path("announcement/<int:pk>/delete/", announcement_views.ann_delete, name="ann_delete"),

    # 任务
    path("task/", task_views.task_list, name="task_list"),
    path("task/add/", task_views.task_add_page, name="task_add"),
    path("task/<int:pk>/edit/", task_views.task_edit, name="task_edit"),
    path("task/<int:pk>/delete/", task_views.task_delete, name="task_delete"),
    path("task/ajax/", task_views.task_ajax, name="task_ajax"),

    # 统计可视化
    path("stats/", stats_views.stats_page, name="stats_page"),
    path("api/stats/dept/", stats_views.api_dept_distribution, name="api_dept_dist"),
    path("api/stats/salary/", stats_views.api_salary_trend, name="api_salary_trend"),
    path("api/stats/attendance/", stats_views.api_attendance_overview, name="api_att_overview"),

    # AI 智能助手
    path("ai/", ai_views.ai_page, name="ai_page"),
    path("ai/api/jd/", ai_views.api_jd, name="ai_jd"),
    path("ai/api/ask/", ai_views.api_ask, name="ai_ask"),
    path("ai/api/comment/", ai_views.api_comment, name="ai_comment"),
    path("ai/api/employee/<int:pk>/comment/", ai_views.api_employee_comment,
         name="ai_emp_comment"),
    path("ai/api/chat/stream/", ai_views.api_chat_stream, name="ai_chat_stream"),
    path("ai/api/chat/clear/", ai_views.api_chat_clear, name="ai_chat_clear"),
]
