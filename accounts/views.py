from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import StudentLecturerSignUpForm

@login_required
def dashboard_redirect_view(request):
    """
    Redirects logged-in users to their role-specific dashboard.
    For now, unbuilt dashboards redirect to placeholders or admin.
    """
    user = request.user

    if user.is_system_admin or user.is_staff:
        return redirect('/admin/')
    elif user.is_lecturer:
        # Will point to lecturer dashboard in Commit 10
        return redirect('/admin/')
    elif user.is_maintenance:
        # Will point to maintenance interface in Commit 11
        return redirect('/admin/')
    else: # Student
        # Will point to student dashboard in Commit 10
        return redirect('/admin/')

def register_view(request):
    if request.method == 'POST':
        form = StudentLecturerSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'accounts/pending_approval.html')
    else:
        form = StudentLecturerSignUpForm()
    
    return render(request, 'accounts/register.html', {'form': form})
