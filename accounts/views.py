from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from apps.accounts.forms import CustomUserCreationForm, EmployerSignUpForm

def signup_view(request):
    return render(request, 'accounts/signup_choice.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            if user.is_employer:
                return redirect('accounts:employer_dashboard')
            return redirect('accounts:jobseeker_dashboard')
    
    return render(request, 'accounts/signup.html') 