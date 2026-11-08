"""认证视图 - 登录、登出、验证码、修改密码."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import ChangePasswordForm, LoginForm
from .utils import generate_captcha


def captcha_view(request):
    """生成图形验证码."""
    img_bytes, code = generate_captcha()
    request.session["captcha"] = code.lower()
    return HttpResponse(img_bytes, content_type="image/png")


def login_view(request):
    """登录页面."""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            captcha = form.cleaned_data["captcha"].lower()

            # 验证码校验
            if captcha != request.session.get("captcha", ""):
                messages.error(request, "验证码错误")
                return render(request, "app01/login.html", {"form": form})

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # 登录后清除验证码
                request.session.pop("captcha", None)
                next_url = request.GET.get("next") or request.POST.get("next") or "/"
                return redirect(next_url)
            else:
                messages.error(request, "用户名或密码错误")
    else:
        form = LoginForm()
    return render(request, "app01/login.html", {"form": form})


def logout_view(request):
    """退出登录."""
    logout(request)
    return redirect("/login/")


def password_change(request):
    """个人中心 - 修改密码（所有角色可用）."""
    if request.method == "POST":
        form = ChangePasswordForm(request.POST, user=request.user)
        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.save(update_fields=["password"])
            # 保持当前会话有效，避免改完密码被踢下线
            update_session_auth_hash(request, request.user)
            messages.success(request, "密码修改成功，下次请使用新密码登录")
            return redirect("password_change")
    else:
        form = ChangePasswordForm(user=request.user)
    return render(request, "app01/password_change.html", {"form": form})

