"""数据统计可视化 - ECharts + AJAX."""
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from . import models
from .decorators import perm_required
from .scoping import scope_by_employee, scope_departments


@perm_required("stats_view")
def stats_page(request):
    """数据统计页面."""
    return render(request, "app01/stats/index.html")


@perm_required("stats_view")
def api_dept_distribution(request):
    """部门人数分布 - 饼图数据（按角色限定部门范围）."""
    try:
        depts = scope_departments(models.Department.objects.all(), request.user)
        data = list(
            depts.annotate(
                count=Count("employee", filter=Q(employee__status=1))
            ).values("name", "count")
        )
        return JsonResponse({"data": data})
    except Exception as e:
        return JsonResponse({"data": [], "error": str(e)}, status=500)


@perm_required("stats_view")
def api_salary_trend(request):
    """各月薪资趋势 - 折线图数据（按角色限定范围）."""
    try:
        from django.db.models.functions import TruncMonth
        qs = scope_by_employee(models.Salary.objects.all(), request.user)
        data = list(
            qs.annotate(month_str=TruncMonth("month"))
            .values("month_str").annotate(total=Sum("total")).order_by("month_str")
        )
        # TruncMonth 返回 datetime，转成字符串
        for d in data:
            if d["month_str"]:
                d["month_str"] = d["month_str"].strftime("%Y-%m")
        return JsonResponse({"data": data})
    except Exception as e:
        return JsonResponse({"data": [], "error": str(e)}, status=500)


@perm_required("stats_view")
def api_attendance_overview(request):
    """考勤概览（按角色限定范围）."""
    try:
        qs = scope_by_employee(models.Attendance.objects.all(), request.user)
        return JsonResponse({
            "data": {
                "total": qs.count(),
                "normal": qs.filter(status="normal").count(),
                "late": qs.filter(status="late").count(),
                "early": qs.filter(status="early").count(),
                "absent": qs.filter(status="absent").count(),
            }
        })
    except Exception as e:
        return JsonResponse({"data": {}, "error": str(e)}, status=500)
