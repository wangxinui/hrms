"""薪资管理 - 实发自动计算."""
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib import messages
from . import models
from .decorators import perm_required
from .forms import SalaryForm
from .scoping import scope_by_employee, scope_employees
from .utils import Pagination
from .views.mixins import CrudMixin


@perm_required("salary_view")
def sal_list(request):
    """薪资列表 + 筛选 + 总额统计 - 按角色限定范围."""
    base_qs = scope_by_employee(
        models.Salary.objects.select_related("employee", "employee__depart"),
        request.user,
    )
    emp_id = request.GET.get("emp", "").strip()
    month = request.GET.get("month", "").strip()
    if emp_id:
        base_qs = base_qs.filter(employee_id=emp_id)
    if month:
        base_qs = base_qs.filter(month__startswith=month[:7])

    qs = base_qs
    total_amount = base_qs.aggregate(Sum("total"))["total__sum"] or 0
    total_count  = base_qs.count()
    avg_amount   = round((total_amount / total_count), 2) if total_count else 0
    stats = {
        "count": total_count,
        "total": round(total_amount, 2),
        "avg":   avg_amount,
    }
    kpis = [
        {"col_class": "col-md-4", "icon_bg": "bg-primary-em", "icon": "fa fa-file-text-o", "label": "薪资记录",     "value": stats["count"]},
        {"col_class": "col-md-4", "icon_bg": "bg-green",     "icon": "fa fa-rmb",         "label": "薪资总额",     "value": "￥" + str(stats["total"])},
        {"col_class": "col-md-4", "icon_bg": "bg-yellow",    "icon": "fa fa-line-chart",  "label": "平均实发",     "value": "￥" + str(stats["avg"])},
    ]

    p = Pagination(qs, request.GET.get("page"), page_size=15, request=request)
    employees = scope_employees(models.Employee.objects.filter(status=1), request.user)
    return render(request, "app01/salary/list.html", {
        "pagination": p, "employees": employees,
        "emp_id": emp_id, "month": month, "total_amount": total_amount,
        "stats": stats, "kpis": kpis,
    })


def _sal_scope_check(request, sal):
    """edit 专用：数据权限检查."""
    if not scope_by_employee(models.Salary.objects.filter(pk=sal.pk), request.user).exists():
        messages.error(request, "您只能维护本部门范围内的薪资")
        return redirect("sal_list")
    return None


@perm_required("salary_add")
def sal_add(request):
    """新增薪资."""
    return CrudMixin.base_add(
        request, SalaryForm, "app01/salary/form.html", "sal_list",
        title="新增薪资", post_save_msg="薪资记录添加成功",
        form_init_kwargs={"user": request.user},
    )


@perm_required("salary_edit")
def sal_edit(request, pk):
    """编辑薪资 - scope 检查."""
    return CrudMixin.base_edit(
        request, pk, models.Salary, SalaryForm,
        "app01/salary/form.html", "sal_list",
        title="编辑薪资", post_save_msg="薪资更新成功",
        obj_ctx_key="sal",
        form_init_kwargs={"user": request.user},
        pre_render=_sal_scope_check,
    )


@perm_required("salary_delete")
def sal_delete(request, pk):
    """删除薪资."""
    return CrudMixin.base_delete(
        request, pk, models.Salary, "sal_list", success_msg="薪资记录已删除",
    )
