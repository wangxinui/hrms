"""首页工作台 - 数据概览（按角色限定范围）."""
from django.shortcuts import render
from . import models
from .scoping import (
    is_employee, my_dept, scope_by_employee, scope_departments, scope_employees,
)


def dashboard(request):
    """仪表盘首页."""
    employees = scope_employees(models.Employee.objects.all(), request.user)
    tasks = scope_by_employee(models.Task.objects.all(), request.user, field="owner")
    attendance = scope_by_employee(models.Attendance.objects.all(), request.user)

    if is_employee(request.user):
        dept_count = 1 if my_dept(request.user) else 0
    else:
        dept_count = scope_departments(
            models.Department.objects.all(), request.user
        ).count()

    stats = {
        "dept_count": dept_count,
        "emp_count": employees.count(),
        "emp_active": employees.filter(status=1).count(),
        "announce_count": models.Announcement.objects.count(),
        "task_todo": tasks.filter(status="todo").count(),
    }
    # 最新公告
    announcements = models.Announcement.objects.all()[:5]
    # 待办任务
    todo_tasks = tasks.filter(status__in=["todo", "doing"])[:5]
    # 最新考勤
    latest_attendance = attendance.select_related("employee", "employee__depart")[:5]

    return render(request, "app01/dashboard.html", {
        "stats": stats,
        "announcements": announcements,
        "tasks": todo_tasks,
        "attendance": latest_attendance,
    })
