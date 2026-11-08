"""考勤管理 - 状态自动计算."""
from datetime import time
from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from .decorators import perm_required
from .forms import AttendanceForm
from .scoping import scope_by_employee, scope_employees
from .utils import Pagination
from .views.mixins import CrudMixin

WORK_START = time(9, 0)
WORK_END = time(18, 0)
LATE_TOLERANCE = 5


def calc_status(clock_in, clock_out):
    """根据打卡时间自动计算考勤状态."""
    if not clock_in and not clock_out:
        return "absent"
    late = False
    early = False
    if clock_in and clock_in > WORK_START:
        from datetime import datetime, timedelta
        dt_in = datetime.combine(datetime.today(), clock_in)
        dt_start = datetime.combine(datetime.today(), WORK_START) + timedelta(minutes=LATE_TOLERANCE)
        if dt_in > dt_start:
            late = True
    if clock_out and clock_out < WORK_END:
        from datetime import datetime, timedelta
        dt_out = datetime.combine(datetime.today(), clock_out)
        dt_end = datetime.combine(datetime.today(), WORK_END) - timedelta(minutes=LATE_TOLERANCE)
        if dt_out < dt_end:
            early = True
    if late and early or late:
        return "late"
    if early:
        return "early"
    if not clock_in or not clock_out:
        return "absent"
    return "normal"


@perm_required("attendance_view")
def att_list(request):
    """考勤列表 - 按角色限定范围."""
    base_qs = scope_by_employee(
        models.Attendance.objects.select_related("employee", "employee__depart"),
        request.user,
    )
    emp_id = request.GET.get("emp", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if emp_id:
        base_qs = base_qs.filter(employee_id=emp_id)
    if date_from:
        base_qs = base_qs.filter(date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(date__lte=date_to)

    qs = base_qs
    stats = {
        "count":  base_qs.count(),
        "normal": base_qs.filter(status="normal").count(),
        "late":   base_qs.filter(status="late").count(),
        "early":  base_qs.filter(status="early").count(),
        "absent": base_qs.filter(status="absent").count(),
    }
    kpis = [
        {"col_class": "col-md-2", "icon_bg": "bg-primary-em", "icon": "fa fa-calendar-check-o","label": "考勤记录", "value": stats["count"]},
        {"col_class": "col-md-2", "icon_bg": "bg-green",     "icon": "fa fa-check-circle",    "label": "按时",     "value": stats["normal"]},
        {"col_class": "col-md-2", "icon_bg": "bg-yellow",    "icon": "fa fa-clock-o",         "label": "迟到",     "value": stats["late"]},
        {"col_class": "col-md-2", "icon_bg": "bg-yellow",    "icon": "fa fa-sign-out",        "label": "早退",     "value": stats["early"]},
        {"col_class": "col-md-2", "icon_bg": "bg-red",       "icon": "fa fa-minus-circle",    "label": "缺勤",     "value": stats["absent"]},
    ]

    p = Pagination(qs, request.GET.get("page"), page_size=15, request=request)
    employees = scope_employees(models.Employee.objects.filter(status=1), request.user)
    return render(request, "app01/attendance/list.html", {
        "pagination": p, "employees": employees,
        "emp_id": emp_id, "date_from": date_from, "date_to": date_to,
        "stats": stats, "kpis": kpis,
    })


def _att_pre_save(obj, request):
    """add/edit 共用的 pre_save：自动计算状态."""
    obj.status = calc_status(obj.clock_in, obj.clock_out)


def _att_scope_check(request, att):
    """edit 专用：数据权限检查，越权则 redirect."""
    if not scope_by_employee(models.Attendance.objects.filter(pk=att.pk), request.user).exists():
        messages.error(request, "您只能维护本部门范围内的考勤")
        return redirect("att_list")
    return None


@perm_required("attendance_add")
def att_add(request):
    """新增考勤 - 自动计算状态."""
    return CrudMixin.base_add(
        request, AttendanceForm, "app01/attendance/form.html", "att_list",
        title="新增考勤", post_save_msg="考勤记录添加成功",
        form_init_kwargs={"user": request.user}, pre_save=_att_pre_save,
    )


@perm_required("attendance_edit")
def att_edit(request, pk):
    """编辑考勤 - scope 检查 + 自动计算状态."""
    return CrudMixin.base_edit(
        request, pk, models.Attendance, AttendanceForm,
        "app01/attendance/form.html", "att_list",
        title="编辑考勤", post_save_msg="考勤更新成功",
        obj_ctx_key="att",
        form_init_kwargs={"user": request.user},
        pre_save=_att_pre_save, pre_render=_att_scope_check,
    )


@perm_required("attendance_delete")
def att_delete(request, pk):
    """删除考勤."""
    return CrudMixin.base_delete(
        request, pk, models.Attendance, "att_list", success_msg="考勤记录已删除",
    )
