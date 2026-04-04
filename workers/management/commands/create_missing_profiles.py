from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from workers.models import WorkerProfile
from employers.models import EmployerProfile

class Command(BaseCommand):
    help = 'Create missing worker and employer profiles for existing users'
    
    def handle(self, *args, **kwargs):
        self.stdout.write("Checking for missing profiles...")
        
        # Create worker profiles for worker users
        workers_created = 0
        worker_users = User.objects.filter(profile__user_type='worker')
        for user in worker_users:
            profile, created = WorkerProfile.objects.get_or_create(user=user)
            if created:
                workers_created += 1
                self.stdout.write(f"Created worker profile for {user.username}")
        
        # Create employer profiles for employer users
        employers_created = 0
        employer_users = User.objects.filter(profile__user_type='employer')
        for user in employer_users:
            profile, created = EmployerProfile.objects.get_or_create(user=user)
            if created:
                employers_created += 1
                self.stdout.write(f"Created employer profile for {user.username}")
        
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {workers_created} worker profiles and {employers_created} employer profiles."
        ))