"""员工管理 CRUD - 按角色限定数据范围."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from . import models
from .decorators import perm_required
from .forms import EmployeeForm
from .scoping import (
    can_access_employee, scope_departments, scope_employees,
)
from .utils import Pagination


@perm_required("employee_view")
def emp_list(request):
    """员工列表 - KPI + 搜索 + 筛选 + 分页."""
    # 权限范围内的基查询集（KPI 和列表共用，避免数字错位）
    base_qs = scope_employees(
        models.Employee.objects.select_related("depart", "user__role"), request.user
    )

    # KPI 统计：看权限范围内的"总盘子"，不受 kw/depart 筛选影响
    stats = {
        "total":  base_qs.count(),
        "active": base_qs.filter(status=1).count(),
        "prob":   base_qs.filter(status=3).count(),
        "left":   base_qs.filter(status=2).count(),
    }
    kpis = [
        {"col_class": "col-md-3", "icon_bg": "bg-primary-em", "icon": "fa fa-users",         "label": "员工总数",   "value": stats["total"]},
        {"col_class": "col-md-3", "icon_bg": "bg-green",     "icon": "fa fa-check-circle", "label": "在职员工",   "value": stats["active"]},
        {"col_class": "col-md-3", "icon_bg": "bg-yellow",    "icon": "fa fa-hourglass-half", "label": "试用期",    "value": stats["prob"]},
        {"col_class": "col-md-3", "icon_bg": "bg-red",       "icon": "fa fa-sign-out",     "label": "已离职",     "value": stats["left"]},
    ]

    qs = base_qs
    kw = request.GET.get("kw", "").strip()
    depart_id = request.GET.get("depart", "").strip()
    if kw:
        qs = qs.filter(name__icontains=kw)
    if depart_id:
        qs = qs.filter(depart_id=depart_id)

    p = Pagination(qs, request.GET.get("page"), page_size=10, request=request)
    departments = scope_departments(models.Department.objects.all(), request.user)
    return render(request, "app01/employee/list.html", {
        "pagination": p, "kw": kw, "depart_id": depart_id,
        "departments": departments, "stats": stats,
        "kpis": kpis,
    })


@perm_required("employee_add")
def emp_add(request):
    """新增员工 - 保存时自动开通登录账号."""
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            emp = form.save()
            account = emp.user.username if emp.user_id else "-"
            messages.success(
                request,
                f"员工添加成功，登录账号 {account}，初始密码 {models.DEFAULT_PASSWORD}",
            )
            return redirect("emp_list")
    else:
        form = EmployeeForm(user=request.user)
    return render(request, "app01/employee/form.html", {
        "form": form, "title": "新增员工",
    })


@perm_required("employee_edit")
def emp_edit(request, pk):
    """编辑员工 — 同时支持整页跳转和抽屉内 AJAX 片段."""
    emp = get_object_or_404(models.Employee, pk=pk)
    if not can_access_employee(request.user, emp):
        messages.error(request, "您只能维护本部门的员工")
        return redirect("emp_list")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=emp, user=request.user)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({"code": 0, "msg": "员工修改成功"})
            messages.success(request, "员工更新成功")
            return redirect("emp_list")
        # form invalid
        if is_ajax:
            # 把 field 错误拍平成 {field_name: [msg1, msg2, ...]}
            errs = {f: [str(e) for e in es] for f, es in form.errors.items()}
            return JsonResponse({"code": 1, "errors": errs}, status=400)
        # 非 AJAX：把 form 带着 errors 渲染回去
    else:
        form = EmployeeForm(instance=emp, user=request.user)

    if is_ajax:
        # 抽屉里要渲染纯表单片段（不带 base.html）
        from django.template.loader import render_to_string
        html = render_to_string(
            "app01/employee/_employee_edit_form.html",
            {"form": form, "title": "编辑员工", "emp": emp},
            request=request,
        )
        return JsonResponse({"code": 0, "html": html})

    return render(request, "app01/employee/form.html", {
        "form": form, "title": "编辑员工", "emp": emp,
    })


@perm_required("employee_delete")
def emp_delete(request, pk):
    """删除员工（仅超级管理员），同时删除其登录账号."""
    emp = get_object_or_404(models.Employee, pk=pk)
    account = emp.user
    emp.delete()
    if account is not None and not account.is_superuser:
        account.delete()
    messages.success(request, "员工及其账号已删除")
    return redirect("emp_list")


@perm_required("employee_view")
def emp_detail(request, pk):
    """员工详情（独立页面）."""
    emp = get_object_or_404(models.Employee.objects.select_related("depart", "user"), pk=pk)
    if not can_access_employee(request.user, emp):
        messages.error(request, "您无权查看该员工档案")
        return redirect("emp_list")
    return render(request, "app01/employee/detail.html", {
        "emp": emp, "default_password": models.DEFAULT_PASSWORD,
    })


@perm_required("employee_view")
def emp_detail_fragment(request, pk):
    """员工详情片段，供列表页抽屉 AJAX 加载，不渲染 base.html."""
    from django.http import HttpResponse
    emp = get_object_or_404(models.Employee.objects.select_related("depart", "user"), pk=pk)
    if not can_access_employee(request.user, emp):
        return HttpResponse("您无权查看该员工档案", status=403)
    return render(request, "app01/employee/_detail_body.html", {
        "emp": emp, "default_password": models.DEFAULT_PASSWORD,
    })


@perm_required("employee_edit")
@require_POST
def emp_reset_password(request, pk):
    """重置员工登录密码为初始密码 — AJAX 友好."""
    emp = get_object_or_404(models.Employee, pk=pk)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not can_access_employee(request.user, emp):
        msg = "您只能维护本部门的员工"
        if is_ajax:
            return JsonResponse({"code": 1, "msg": msg}, status=403)
        messages.error(request, msg)
        return redirect("emp_list")
    if emp.user_id is None:
        emp.ensure_account()
        msg = f"已为 {emp.name} 开通账号，初始密码 {models.DEFAULT_PASSWORD}"
        if is_ajax:
            return JsonResponse({"code": 0, "msg": msg})
        messages.success(request, msg)
        return redirect("emp_detail", pk=emp.pk)
    if emp.user.is_superuser:
        msg = "超级管理员密码不允许在此重置"
        if is_ajax:
            return JsonResponse({"code": 1, "msg": msg}, status=400)
        messages.error(request, msg)
        return redirect("emp_detail", pk=emp.pk)
    emp.user.set_password(models.DEFAULT_PASSWORD)
    emp.user.save(update_fields=["password"])
    msg = f"已将 {emp.name} 的密码重置为 {models.DEFAULT_PASSWORD}"
    if is_ajax:
        return JsonResponse({"code": 0, "msg": msg})
    messages.success(request, msg)
    return redirect("emp_detail", pk=emp.pk)
