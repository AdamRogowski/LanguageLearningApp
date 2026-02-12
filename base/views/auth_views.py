"""Authentication views: login, logout, and registration."""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST


def loginPage(request):
    """Handle user login."""
    page = "login"
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            # Generic message to avoid user enumeration attacks
            messages.error(request, "Invalid username or password.")

    context = {"page": page}
    return render(request, "base/unauthenticated/login_register.html", context)


@require_POST
def logoutUser(request):
    """Handle user logout."""
    logout(request)
    messages.info(request, "User was logged out")
    return redirect("home")


def registerPage(request):
    """Handle user registration."""
    page = "register"
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username
            user.save()
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "An error occurred during registration")

    context = {"form": form, "page": page}
    return render(request, "base/unauthenticated/login_register.html", context)
