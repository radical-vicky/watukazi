from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.urls import reverse
from .forms import WorkerSignupForm, EmployerSignupForm

def home_page(request):
    return render(request, 'home.html')

# Custom Worker Signup View
def worker_signup(request):
    if request.method == 'POST':
        form = WorkerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, f"Welcome {user.first_name}! You have successfully registered as a WORKER.")
            return redirect('workers:dashboard')
    else:
        form = WorkerSignupForm()
    return render(request, 'account/worker_signup.html', {'form': form})

# Custom Employer Signup View
def employer_signup(request):
    if request.method == 'POST':
        form = EmployerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, f"Welcome {user.first_name}! You have successfully registered as an EMPLOYER.")
            return redirect('employers:dashboard')
    else:
        form = EmployerSignupForm()
    return render(request, 'account/employer_signup.html', {'form': form})

# Custom Worker Login View
def worker_login(request):
    # Get the next parameter from the URL
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        username = request.POST.get('login')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if hasattr(user, 'profile') and user.profile.user_type == 'worker':
                login(request, user)
                messages.success(request, f"Welcome back {user.username}!")
                
                # If there's a next URL, redirect there
                if next_url:
                    return redirect(next_url)
                return redirect('workers:dashboard')
            else:
                messages.error(request, "This account is not a worker account. Please use the employer login page.")
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'account/worker_login.html', {'next': next_url})

# Custom Employer Login View
def employer_login(request):
    # Get the next parameter from the URL
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        username = request.POST.get('login')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if hasattr(user, 'profile') and user.profile.user_type == 'employer':
                login(request, user)
                messages.success(request, f"Welcome back {user.username}!")
                
                # If there's a next URL, redirect there
                if next_url:
                    return redirect(next_url)
                return redirect('employers:dashboard')
            else:
                messages.error(request, "This account is not an employer account. Please use the worker login page.")
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'account/employer_login.html', {'next': next_url})