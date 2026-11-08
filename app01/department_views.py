"""部门管理 CRUD."""
from django.shortcuts import render
from . import models
from .decorators import perm_required
from .forms import DepartmentForm
from .scoping import scope_departments, scope_employees
from .utils import Pagination
from .views.mixins import CrudMixin


@perm_required("department_view")
def dept_list(request):
    """部门列表 - 部门管理员只看本科室及下级."""
    base_qs = scope_departments(
        models.Department.objects.select_related("parent"), request.user
    )
    kw = request.GET.get("kw", "").strip()
    qs = base_qs
    if kw:
        qs = qs.filter(name__icontains=kw)
    stats = {
        "total":        base_qs.count(),
        "top_level":    base_qs.filter(parent__isnull=True).count(),
        "with_manager": base_qs.filter(manager__isnull=False).count(),
    }
    stats["employees"] = scope_employees(
        models.Employee.objects.filter(status=1), request.user
    ).count()
    kpis = [
        {"col_class": "col-md-3", "icon_bg": "bg-primary-em", "icon": "fa fa-sitemap",    "label": "部门总数",     "value": stats["total"]},
        {"col_class": "col-md-3", "icon_bg": "bg-aqua",      "icon": "fa fa-building",   "label": "顶级部门",     "value": stats["top_level"]},
        {"col_class": "col-md-3", "icon_bg": "bg-green",     "icon": "fa fa-user-circle","label": "已任命负责人", "value": stats["with_manager"]},
        {"col_class": "col-md-3", "icon_bg": "bg-yellow",    "icon": "fa fa-users",      "label": "在职员工总数", "value": stats["employees"]},
    ]
    p = Pagination(qs, request.GET.get("page"), page_size=10, request=request)
    return render(request, "app01/department/list.html", {
        "pagination": p, "kw": kw, "stats": stats, "kpis": kpis,
    })


@perm_required("department_add")
def dept_add(request):
    """新增部门."""
    return CrudMixin.base_add(
        request, DepartmentForm, "app01/department/form.html", "dept_list",
        title="新增部门", post_save_msg="部门添加成功",
    )


@perm_required("department_edit")
def dept_edit(request, pk):
    """编辑部门."""
    return CrudMixin.base_edit(
        request, pk, models.Department, DepartmentForm,
        "app01/department/form.html", "dept_list",
        title="编辑部门", post_save_msg="部门更新成功",
        obj_ctx_key="dept",
    )


@perm_required("department_delete")
def dept_delete(request, pk):
    """删除部门."""
    return CrudMixin.base_delete(
        request, pk, models.Department, "dept_list",
        success_msg="部门已删除",
    )
