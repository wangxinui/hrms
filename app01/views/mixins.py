"""视图通用骨架 - CrudMixin.

提供 add / edit / delete 三个标准 CRUD 骨架函数，
各模块只需传入 Form / Model / template / redirect_name 以及少量 hook。
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse


class CrudMixin:
    """CRUD 三个标准骨架函数。

    通用参数：
      FormClass        — Django Form 类
      Model            — Django Model 类（edit/delete 用）
      template         — 模板路径
      redirect_name    — messages 成功后 redirect 的 url name

    可选参数（**kwargs）：
      title            — 模板 context 里的标题
      post_save_msg    — 保存成功后的 messages.success 文本
      form_init_kwargs — 传给 Form 的额外 kwargs（如 {"user": request.user}）
      extra_ctx        — 额外注入模板 context 的 dict
      pre_save(obj, request) — 对象 save() 前的回调
      pre_render(request, obj) — render 前回调，返回 redirect 则中断，否则 None
      obj_ctx_key      — edit 时 obj 注入 ctx 的 key（如 "dept"/"ann"/"att"/"sal"）
    """

    @staticmethod
    def base_add(request, FormClass, template, redirect_name, **kwargs):
        title = kwargs.get("title", "新增")
        post_save_msg = kwargs.get("post_save_msg", "添加成功")
        form_init_kwargs = kwargs.get("form_init_kwargs", {})
        extra_ctx = kwargs.get("extra_ctx") or {}
        pre_save = kwargs.get("pre_save")

        if request.method == "POST":
            form = FormClass(request.POST, request.FILES or None, **form_init_kwargs)
            if form.is_valid():
                obj = form.save(commit=False)
                if pre_save:
                    pre_save(obj, request)
                obj.save()
                messages.success(request, post_save_msg)
                return redirect(redirect_name)
        else:
            form = FormClass(**form_init_kwargs)

        ctx = {"form": form, "title": title}
        ctx.update(extra_ctx)
        return render(request, template, ctx)

    @staticmethod
    def base_edit(request, pk, Model, FormClass, template, redirect_name, **kwargs):
        title = kwargs.get("title", "编辑")
        post_save_msg = kwargs.get("post_save_msg", "修改成功")
        form_init_kwargs = kwargs.get("form_init_kwargs", {})
        extra_ctx = kwargs.get("extra_ctx") or {}
        pre_save = kwargs.get("pre_save")
        pre_render = kwargs.get("pre_render")
        obj_ctx_key = kwargs.get("obj_ctx_key")

        obj = get_object_or_404(Model, pk=pk)

        if pre_render:
            early = pre_render(request, obj)
            if early:
                return early

        if request.method == "POST":
            form = FormClass(
                request.POST, request.FILES or None,
                instance=obj, **form_init_kwargs
            )
            if form.is_valid():
                obj = form.save(commit=False)
                if pre_save:
                    pre_save(obj, request)
                obj.save()
                messages.success(request, post_save_msg)
                return redirect(redirect_name)
        else:
            form = FormClass(instance=obj, **form_init_kwargs)

        ctx = {"form": form, "title": title}
        ctx.update(extra_ctx)
        if obj_ctx_key:
            ctx[obj_ctx_key] = obj
        return render(request, template, ctx)

    @staticmethod
    def base_delete(request, pk, Model, redirect_name,
                    success_msg="删除成功",
                    is_ajax=False):
        """标准删除（POST 执行）."""
        obj = get_object_or_404(Model, pk=pk)
        if request.method == "POST":
            try:
                obj.delete()
                if is_ajax:
                    return JsonResponse({"code": 0, "msg": success_msg})
                messages.success(request, success_msg)
            except Exception as e:
                if is_ajax:
                    return JsonResponse({"code": 1, "msg": f"删除失败: {e}"})
                messages.error(request, f"删除失败: {e}")
            return redirect(redirect_name)

        ctx = {"object": obj, "title": "确认删除"}
        return render(request, "app01/confirm_delete.html", ctx)
