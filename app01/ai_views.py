"""AI 智能助手视图.

T2 招聘 JD 生成 / T3 制度问答 / T4 数据点评 /
T5 多轮对话 / T6 安全兜底 / T7 SSE 流式输出
"""
import json
import logging
import re
from collections import Counter
from datetime import date

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from . import models
from .decorators import perm_required
from .scoping import can_access_employee, my_employee, scope_employees
from .utils.ai import (
    COMMENT_SYSTEM, JD_SYSTEM, KB_SYSTEM,
    InputRejected, LLMClient, LLMError, build_chat_system, build_comment_prompt,
    build_jd_prompt, build_kb_prompt, check_input,
)
from .utils.rag import search_knowledge

logger = logging.getLogger("app01.ai")


# ── 通用工具 ──────────────────────────────────────────────────────────

def _read_json(request):
    """容错读取 JSON 请求体，解析失败返回空字典."""
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _fail(message, code=1, status=200):
    return JsonResponse({"code": code, "msg": message}, status=status)


def _ok(data):
    return JsonResponse({"code": 0, "data": data})


def _sse(payload):
    """打包一条 SSE 事件."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _resolve_month(employee, raw):
    """把 YYYY-MM 解析为该月 1 号；未提供时取最近有数据的月份."""
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", (raw or "").strip())
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return date(year, month, 1)
    latest = (
        models.Salary.objects.filter(employee=employee)
        .order_by("-month").values_list("month", flat=True).first()
    )
    if latest:
        return latest
    latest_date = (
        models.Attendance.objects.filter(employee=employee)
        .order_by("-date").values_list("date", flat=True).first()
    )
    if latest_date:
        return latest_date.replace(day=1)
    return date.today().replace(day=1)


def _month_stats(employee, month):
    """汇总某员工某月的考勤与薪资，转为可注入提示词的文本."""
    attendance = models.Attendance.objects.filter(
        employee=employee, date__year=month.year, date__month=month.month
    )
    counts = dict(
        attendance.values_list("status").annotate(total=Count("id"))
    )
    if counts:
        total = sum(counts.values())
        attendance_text = (
            f"考勤：当月记录 {total} 天，按时 {counts.get('normal', 0)} 天，"
            f"迟到 {counts.get('late', 0)} 天，早退 {counts.get('early', 0)} 天，"
            f"缺勤 {counts.get('absent', 0)} 天。"
        )
    else:
        attendance_text = "考勤：该月暂无考勤记录。"

    salary = models.Salary.objects.filter(employee=employee, month=month).first()
    if salary:
        salary_text = (
            f"薪资：基本工资 {salary.base_salary} 元，奖金 {salary.bonus} 元，"
            f"扣款 {salary.deduction} 元，实发 {salary.total} 元。"
        )
    else:
        salary_text = "薪资：该月暂无薪资记录。"
    return f"{attendance_text}\n{salary_text}"


def _comment_reply(employee, raw_month):
    """生成某员工某月的 AI 点评，返回 (月份文本, 点评内容)."""
    month = _resolve_month(employee, raw_month)
    stats_text = _month_stats(employee, month)
    prompt = build_comment_prompt(
        employee.name, employee.depart.name, month.strftime("%Y-%m"), stats_text
    )
    answer = LLMClient().chat(
        prompt, system=COMMENT_SYSTEM, temperature=0.5, max_tokens=500
    )
    return month.strftime("%Y-%m"), answer


# ── 页面 ──────────────────────────────────────────────────────────────

@perm_required("ai_view")
def ai_page(request):
    """AI 工作台：多轮对话 / JD / 制度问答 / 数据点评."""
    employees = scope_employees(
        models.Employee.objects.select_related("depart").filter(status=1),
        request.user,
    ).order_by("name")
    return render(request, "app01/ai/index.html", {
        "employees": employees,
        "chat_history": request.session.get("ai_chat_history", []),
        "llm_model": settings.LLM_MODEL,
        "llm_ready": bool(settings.LLM_API_KEY),
        "max_input": settings.LLM_MAX_INPUT,
    })


# ── T2 招聘 JD ────────────────────────────────────────────────────────

@perm_required("ai_view")
@require_POST
def api_jd(request):
    data = _read_json(request)
    try:
        job_title = check_input(data.get("job_title"), max_len=30)
    except InputRejected as exc:
        return _fail(str(exc))
    department = (data.get("department") or "").strip()[:30]
    experience = (data.get("experience") or "不限").strip()[:20]

    prompt = build_jd_prompt(job_title, department, experience)
    try:
        content = LLMClient().chat(prompt, system=JD_SYSTEM, max_tokens=1000)
    except LLMError as exc:
        return _fail(str(exc))
    return _ok({"job_title": job_title, "content": content})


# ── T3 制度知识库问答 ─────────────────────────────────────────────────

@perm_required("ai_view")
@require_POST
def api_ask(request):
    data = _read_json(request)
    try:
        question = check_input(data.get("question"))
    except InputRejected as exc:
        return _fail(str(exc))

    docs = search_knowledge(question, limit=3)
    if not docs:
        # 检索不到资料就不调用模型，从源头避免编造
        return _ok({
            "answer": "不知道。公司制度库中没有检索到与该问题相关的条款，建议咨询人力资源部。",
            "sources": [],
        })

    try:
        answer = LLMClient().chat(
            build_kb_prompt(question, docs), system=KB_SYSTEM,
            temperature=0.2, max_tokens=600,
        )
    except LLMError as exc:
        return _fail(str(exc))

    return _ok({
        "answer": answer,
        "sources": [
            {"id": doc.id, "title": doc.title, "category": doc.get_category_display()}
            for doc in docs
        ],
    })


# ── T4 数据智能点评 ───────────────────────────────────────────────────

@perm_required("ai_view")
@require_POST
def api_comment(request):
    data = _read_json(request)
    employee_id = data.get("employee_id")
    if not employee_id:
        return _fail("请先选择员工")

    employee = (
        models.Employee.objects.select_related("depart")
        .filter(pk=employee_id).first()
    )
    if employee is None:
        return _fail("员工不存在或已被删除")
    if not can_access_employee(request.user, employee):
        return _fail("您没有权限查看该员工的数据", status=403)

    try:
        month_label, answer = _comment_reply(employee, data.get("month"))
    except LLMError as exc:
        return _fail(str(exc))
    return _ok({
        "employee": employee.name,
        "department": employee.depart.name,
        "month": month_label,
        "answer": answer,
    })


@perm_required("ai_view")
@require_POST
def api_employee_comment(request, pk):
    """页面内嵌入口：员工详情 / 薪资列表的「AI 点评」按钮."""
    employee = (
        models.Employee.objects.select_related("depart")
        .filter(pk=pk).first()
    )
    if employee is None:
        return _fail("员工不存在或已被删除")
    if not can_access_employee(request.user, employee):
        return _fail("您没有权限查看该员工的数据", status=403)

    data = _read_json(request)
    try:
        month_label, answer = _comment_reply(employee, data.get("month"))
    except LLMError as exc:
        return _fail(str(exc))
    return _ok({
        "employee": employee.name,
        "department": employee.depart.name,
        "month": month_label,
        "answer": answer,
    })


# ── T5 + T7 多轮对话（SSE 流式） ──────────────────────────────────────

def _employee_notes(message, user):
    """提取消息中提到的员工，按权限与数据范围分层披露信息.

    基础档案：在数据范围内即可见；
    薪资/考勤：需要对应权限码，且必须通过数据范围校验；
    手机号：仅超级管理员或本人可见。
    """
    names = []
    for name in models.Employee.objects.values_list("name", flat=True):
        if name and name in message and name not in names:
            names.append(name)

    self_hint = any(word in message for word in ("我", "本人", "自己"))
    if not names and not self_hint:
        return []

    perms = set()
    if not user.is_superuser and user.role_id:
        perms = set(user.role.permissions.values_list("code", flat=True))

    targets = []
    if names:
        qs = models.Employee.objects.filter(name__in=names[:3]).select_related("depart")
        targets = list(scope_employees(qs, user)[:2])
    if self_hint:
        me = my_employee(user)
        if me and all(me.pk != emp.pk for emp in targets):
            targets.insert(0, me)

    notes = []
    for emp in targets[:2]:
        dept = emp.depart.name if emp.depart_id else "未分配部门"
        lines = [f"{emp.name}：{dept}，{emp.get_status_display()}，{emp.hire_date} 入职"]

        allowed = can_access_employee(user, emp)

        if allowed and (user.is_superuser or "salary_view" in perms):
            latest = models.Salary.objects.filter(employee=emp).order_by("-month").first()
            if latest:
                lines.append(f"最近薪资：{latest.month:%Y-%m} 实发 {latest.total} 元")

        if allowed and (user.is_superuser or "attendance_view" in perms):
            last = models.Attendance.objects.filter(employee=emp).order_by("-date").first()
            if last:
                start = last.date.replace(day=1)
                rows = models.Attendance.objects.filter(
                    employee=emp, date__gte=start, date__lte=last.date
                ).values_list("status", flat=True)
                counts = Counter(rows)
                lines.append(
                    f"{start:%Y-%m} 考勤：按时 {counts['normal']} 天，迟到 {counts['late']} 次，"
                    f"早退 {counts['early']} 次，缺勤 {counts['absent']} 次"
                )

        if user.is_superuser or emp.user_id == user.id:
            lines.append(f"手机号：{emp.phone}")

        notes.append("；".join(lines))

    if not notes:
        if names:
            notes.append(f"系统中没有你权限范围内的员工：{'、'.join(names[:3])}")
        else:
            notes.append("当前登录账号未关联员工档案，无法查询个人考勤/薪资")
    return notes


@perm_required("ai_view")
@require_POST
def api_chat_stream(request):
    data = _read_json(request)
    try:
        message = check_input(data.get("message"))
    except InputRejected as exc:
        return _fail(str(exc))

    history = request.session.get("ai_chat_history", [])
    keep = settings.LLM_HISTORY_ROUNDS * 2

    # 对话前先做两件事：召回制度资料 + 提取被问到的员工（均受数据范围限制）
    docs = search_knowledge(message, limit=3)
    employee_notes = _employee_notes(message, request.user)
    system = build_chat_system(docs=docs, employee_notes=employee_notes)

    messages = [{"role": "system", "content": system}]
    for item in history[-keep:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})

    client = LLMClient()

    def event_stream():
        parts = []
        try:
            for chunk in client.stream(messages, temperature=0.3, max_tokens=800):
                parts.append(chunk)
                yield _sse({"type": "delta", "content": chunk})
        except LLMError as exc:
            yield _sse({"type": "error", "msg": str(exc)})
            yield _sse({"type": "done"})
            return

        answer = "".join(parts).strip()
        if answer:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": answer})
            request.session["ai_chat_history"] = history[-keep:]
            request.session.modified = True
            try:
                request.session.save()
            except Exception:  # noqa: BLE001 - 会话落库失败不影响本次回答
                logger.exception("对话历史写入 session 失败")
        else:
            yield _sse({"type": "error", "msg": "AI 没有返回内容，请换个问法再试。"})
        yield _sse({"type": "done"})

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@perm_required("ai_view")
@require_POST
def api_chat_clear(request):
    request.session.pop("ai_chat_history", None)
    request.session.modified = True
    return JsonResponse({"code": 0, "msg": "对话已清空"})
