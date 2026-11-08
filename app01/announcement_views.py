"""公告管理 - 置顶、搜索、分页."""
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from . import models
from .decorators import perm_required
from .forms import AnnouncementForm
from .utils import Pagination
from .views.mixins import CrudMixin


@perm_required("announcement_view")
def ann_list(request):
    """公告列表 - 置顶优先."""
    base_qs = models.Announcement.objects.all().select_related("publisher")
    kw = request.GET.get("kw", "").strip()
    qs = base_qs
    if kw:
        qs = qs.filter(title__icontains=kw) | qs.filter(content__icontains=kw)
    now = timezone.now()
    stats = {
        "total":      base_qs.count(),
        "top":        base_qs.filter(is_top=True).count(),
        "this_month": base_qs.filter(created_at__year=now.year, created_at__month=now.month).count(),
    }
    kpis = [
        {"col_class": "col-md-4", "icon_bg": "bg-primary-em", "icon": "fa fa-bullhorn",   "label": "公告总数", "value": stats["total"]},
        {"col_class": "col-md-4", "icon_bg": "bg-red",       "icon": "fa fa-thumb-tack","label": "置顶公告", "value": stats["top"]},
        {"col_class": "col-md-4", "icon_bg": "bg-green",     "icon": "fa fa-calendar",  "label": "本月发布", "value": stats["this_month"]},
    ]
    p = Pagination(qs, request.GET.get("page"), page_size=10, request=request)
    return render(request, "app01/announcement/list.html", {
        "pagination": p, "kw": kw, "stats": stats, "kpis": kpis,
    })


@perm_required("announcement_add")
def ann_add(request):
    """发布公告 - pre_save 注入 publisher."""
    def _pre_save(obj, req):
        obj.publisher = req.user

    return CrudMixin.base_add(
        request, AnnouncementForm, "app01/announcement/form.html", "ann_list",
        title="发布公告", post_save_msg="公告发布成功", pre_save=_pre_save,
    )


@perm_required("announcement_edit")
def ann_edit(request, pk):
    """编辑公告."""
    return CrudMixin.base_edit(
        request, pk, models.Announcement, AnnouncementForm,
        "app01/announcement/form.html", "ann_list",
        title="编辑公告", post_save_msg="公告更新成功", obj_ctx_key="ann",
    )


@perm_required("announcement_edit")
def ann_toggle_top(request, pk):
    """切换置顶状态."""
    ann = get_object_or_404(models.Announcement, pk=pk)
    ann.is_top = not ann.is_top
    ann.save()
    from django.contrib import messages
    messages.success(request, "置顶状态已更新")
    return redirect("ann_list")


@perm_required("announcement_delete")
def ann_delete(request, pk):
    """删除公告."""
    return CrudMixin.base_delete(
        request, pk, models.Announcement, "ann_list", success_msg="公告已删除",
    )
