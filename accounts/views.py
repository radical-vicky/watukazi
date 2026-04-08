from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.urls import reverse
from .forms import WorkerSignupForm, EmployerSignupForm
from .models import Profile

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
    
    # If user is already logged in
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'worker':
                return redirect('workers:dashboard')
            elif request.user.profile.user_type == 'employer':
                return redirect('employers:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('login')
        password = request.POST.get('password')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has a profile
            if not hasattr(user, 'profile'):
                # Create profile if missing
                Profile.objects.create(
                    user=user,
                    phone_number=f"AUTO_{user.id}",
                    user_type='worker'
                )
            
            # Check if user is a worker
            if user.profile.user_type == 'worker':
                login(request, user)
                messages.success(request, f"Welcome back {user.username}!")
                
                # If there's a next URL, redirect there
                if next_url:
                    return redirect(next_url)
                return redirect('workers:dashboard')
            else:
                messages.error(request, "This account is not a worker account. Please use the employer login page.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    
    return render(request, 'account/worker_login.html', {'next': next_url})

# Custom Employer Login View
def employer_login(request):
    # Get the next parameter from the URL
    next_url = request.GET.get('next', '')
    
    # If user is already logged in
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'employer':
                return redirect('employers:dashboard')
            elif request.user.profile.user_type == 'worker':
                return redirect('workers:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('login')
        password = request.POST.get('password')
        
        # Debug: Print to console
        print(f"Employer login attempt - Username: {username}")
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has a profile
            if not hasattr(user, 'profile'):
                # Create profile if missing
                Profile.objects.create(
                    user=user,
                    phone_number=f"AUTO_{user.id}",
                    user_type='employer'
                )
                print(f"Created missing profile for {user.username}")
            
            # Check if employer profile exists, if yes, ensure user_type is employer
            from employers.models import EmployerProfile
            if EmployerProfile.objects.filter(user=user).exists():
                if user.profile.user_type != 'employer':
                    user.profile.user_type = 'employer'
                    user.profile.save()
                    print(f"Fixed user type to employer for {user.username}")
            
            print(f"User found: {user.username}, User type: {user.profile.user_type}")
            
            # Check if user is an employer
            if user.profile.user_type == 'employer':
                login(request, user)
                messages.success(request, f"Welcome back {user.username}!")
                
                # If there's a next URL, redirect there
                if next_url:
                    return redirect(next_url)
                return redirect('employers:dashboard')
            else:
                messages.error(request, f"This account is a {user.profile.user_type} account. Please use the correct login page.")
        else:
            print("Authentication failed")
            messages.error(request, "Invalid username or password. Please try again.")
    
    return render(request, 'account/employer_login.html', {'next': next_url})

# Custom logout view
def custom_logout(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('accounts:home')