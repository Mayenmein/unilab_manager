from django.shortcuts import render
from .forms import StudentLecturerSignUpForm

def register_view(request):
    if request.method == 'POST':
        form = StudentLecturerSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'accounts/pending_approval.html')
    else:
        form = StudentLecturerSignUpForm()
    
    return render(request, 'accounts/register.html', {'form': form})
