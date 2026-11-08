"""任务管理 - AJAX 异步提交."""
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from . import models
from .decorators import perm_required
from .forms import TaskForm
from .scoping import scope_by_employee
from .utils import Pagination


def _in_scope(user, pk):
    """任务是否在当前用户的数据范围内."""
    return scope_by_employee(
        models.Task.objects.filter(pk=pk), user, field="owner"
    ).exists()


@perm_required("task_view")
def task_list(request):
    """任务列表 - 按角色限定范围."""
    base_qs = scope_by_employee(
        models.Task.objects.select_related("owner", "owner__depart"),
        request.user, field="owner",
    )
    level = request.GET.get("level", "").strip()
    status = request.GET.get("status", "").strip()
    qs = base_qs
    if level:
        qs = qs.filter(level=level)
    if status:
        qs = qs.filter(status=status)
    # KPI（base_qs 不含 level/status 筛选）
    stats = {
        "total": base_qs.count(),
        "todo":  base_qs.filter(status="todo").count(),
        "doing": base_qs.filter(status="doing").count(),
        "done":  base_qs.filter(status="done").count(),
    }
    kpis = [
        {"col_class": "col-md-3", "icon_bg": "bg-primary-em", "icon": "fa fa-list-alt", "label": "任务总数", "value": stats["total"]},
        {"col_class": "col-md-3", "icon_bg": "bg-gray",      "icon": "fa fa-circle-o", "label": "待处理",   "value": stats["todo"]},
        {"col_class": "col-md-3", "icon_bg": "bg-yellow",    "icon": "fa fa-spinner",  "label": "进行中",   "value": stats["doing"]},
        {"col_class": "col-md-3", "icon_bg": "bg-green",     "icon": "fa fa-check-circle", "label": "已完成", "value": stats["done"]},
    ]
    p = Pagination(qs, request.GET.get("page"), page_size=10, request=request)
    return render(request, "app01/task/list.html", {
        "pagination": p, "level": level, "status": status, "stats": stats,
        "kpis": kpis,
    })


@perm_required("task_add")
def task_add_page(request):
    """任务新增页面 - 支持 AJAX 和普通提交."""
    if request.method == "POST":
        # AJAX 提交
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form = TaskForm(request.POST, user=request.user)
            if form.is_valid():
                form.save()
                return JsonResponse({"code": 0, "msg": "任务创建成功"})
            # 把错误转为 dict
            errors = {k: v.get_json_data() for k, v in form.errors.items()}
            return JsonResponse({"code": 1, "msg": "校验失败", "errors": errors})
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "任务创建成功")
            return redirect("task_list")
    else:
        form = TaskForm(user=request.user)
    return render(request, "app01/task/form.html", {
        "form": form, "title": "新建任务",
    })


@perm_required("task_edit")
def task_edit(request, pk):
    """编辑任务."""
    task = get_object_or_404(models.Task, pk=pk)
    if not _in_scope(request.user, pk):
        messages.error(request, "您只能维护本人或本部门的任务")
        return redirect("task_list")
    if request.method == "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form = TaskForm(request.POST, instance=task, user=request.user)
            if form.is_valid():
                form.save()
                return JsonResponse({"code": 0, "msg": "更新成功"})
            errors = {k: v.get_json_data() for k, v in form.errors.items()}
            return JsonResponse({"code": 1, "msg": "校验失败", "errors": errors})
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "任务更新成功")
            return redirect("task_list")
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, "app01/task/form.html", {
        "form": form, "title": "编辑任务", "task": task,
    })


@perm_required("task_delete")
def task_delete(request, pk):
    """删除任务."""
    task = get_object_or_404(models.Task, pk=pk)
    if not _in_scope(request.user, pk):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"code": 403, "msg": "您没有权限删除该任务"}, status=403)
        messages.error(request, "您只能删除本人或本部门的任务")
        return redirect("task_list")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        task.delete()
        return JsonResponse({"code": 0, "msg": "删除成功"})
    task.delete()
    messages.success(request, "任务已删除")
    return redirect("task_list")


@perm_required("task_add")
@require_POST
@csrf_exempt
def task_ajax(request):
    """纯 AJAX 任务提交接口."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"code": 1, "msg": "请求格式错误"})
    form = TaskForm(data, user=request.user)
    if form.is_valid():
        form.save()
        return JsonResponse({"code": 0, "msg": "任务创建成功"})
    errors = {k: v.get_json_data() for k, v in form.errors.items()}
    return JsonResponse({"code": 1, "msg": "校验失败", "errors": errors})
