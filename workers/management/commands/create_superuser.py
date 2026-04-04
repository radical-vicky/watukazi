from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create admin superuser for Watukazi system'
    
    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                'admin',
                'admin@watukazi.co.ke',
                'admin123'
            )
            admin.first_name = 'System'
            admin.last_name = 'Administrator'
            admin.save()
            
            admin.profile.user_type = 'admin'
            admin.profile.phone_number = '0700000000'
            admin.profile.is_verified = True
            admin.profile.save()
            
            self.stdout.write(self.style.SUCCESS('Superuser created: admin / password: admin123'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists'))