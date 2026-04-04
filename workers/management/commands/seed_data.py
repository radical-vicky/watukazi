from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from workers.models import Skill, SkillCategory
from employers.models import EmployerProfile
from jobs.models import JobRequest, JobMatch

class Command(BaseCommand):
    help = 'Seed initial data for Watukazi system'
    
    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Watukazi system data...")
        
        # Create skill categories
        categories = [
            'Construction', 'Plumbing', 'Electrical', 'Carpentry',
            'Painting', 'Cleaning', 'Gardening', 'Transport',
            'Repair & Maintenance', 'Domestic Services'
        ]
        
        for cat in categories:
            SkillCategory.objects.get_or_create(name=cat)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} skill categories'))
        
        # Create skills
        skills_data = {
            'Construction': ['Masonry', 'Roofing', 'Tiling', 'Welding', 'Steel Fixing'],
            'Plumbing': ['Pipe Fitting', 'Bathroom Installation', 'Water Heater Repair', 'Drainage'],
            'Electrical': ['Wiring', 'Socket Installation', 'Lighting', 'Circuit Repair'],
            'Carpentry': ['Furniture Making', 'Cabinet Installation', 'Wood Carving', 'Flooring'],
            'Painting': ['Interior Painting', 'Exterior Painting', 'Spray Painting', 'Wallpaper'],
            'Cleaning': ['House Cleaning', 'Office Cleaning', 'Carpet Cleaning', 'Window Cleaning'],
            'Gardening': ['Lawn Mowing', 'Tree Trimming', 'Landscaping', 'Irrigation'],
            'Transport': ['Driving', 'Delivery', 'Moving Services', 'Courier'],
            'Repair & Maintenance': ['Appliance Repair', 'Phone Repair', 'Bicycle Repair', 'Furniture Repair'],
            'Domestic Services': ['Cooking', 'Childcare', 'Elderly Care', 'Laundry']
        }
        
        skill_count = 0
        for category_name, skills in skills_data.items():
            category = SkillCategory.objects.get(name=category_name)
            for skill_name in skills:
                Skill.objects.get_or_create(name=skill_name, category=category)
                skill_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {skill_count} skills'))
        
        # Create test worker account
        if not User.objects.filter(username='worker_demo').exists():
            worker = User.objects.create_user(
                'worker_demo', 
                'worker@watukazi.co.ke', 
                'worker123'
            )
            worker.first_name = 'John'
            worker.last_name = 'Mwangi'
            worker.save()
            
            worker.profile.user_type = 'worker'
            worker.profile.phone_number = '0712345678'
            worker.profile.location = 'Nairobi'
            worker.profile.county = 'Nairobi'
            worker.profile.save()
            
            # Create worker profile
            from workers.models import WorkerProfile
            worker_profile = WorkerProfile.objects.create(
                user=worker,
                years_experience=5,
                hourly_rate=500,
                daily_rate=3500,
                bio="Experienced handyman with 5 years in construction and repairs"
            )
            
            # Add skills
            worker_profile.skills.add(
                Skill.objects.get(name='Masonry'),
                Skill.objects.get(name='Pipe Fitting'),
                Skill.objects.get(name='Wiring'),
                Skill.objects.get(name='Painting')
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created worker: worker_demo / password: worker123'))
        
        # Create test employer account
        if not User.objects.filter(username='employer_demo').exists():
            employer = User.objects.create_user(
                'employer_demo', 
                'employer@watukazi.co.ke', 
                'employer123'
            )
            employer.first_name = 'Sarah'
            employer.last_name = 'Njeri'
            employer.save()
            
            employer.profile.user_type = 'employer'
            employer.profile.phone_number = '0723456789'
            employer.profile.location = 'Nairobi'
            employer.profile.county = 'Nairobi'
            employer.profile.save()
            
            # Create employer profile
            EmployerProfile.objects.create(
                user=employer,
                company_name='Njeri Construction Ltd',
                is_verified_business=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created employer: employer_demo / password: employer123'))
        
        # Create sample job
        if not JobRequest.objects.filter(title__icontains='Construction').exists():
            employer = User.objects.get(username='employer_demo')
            worker = User.objects.get(username='worker_demo')
            
            job = JobRequest.objects.create(
                employer=employer,
                title='Need Mason for House Construction',
                description='Looking for an experienced mason for a residential construction project in Nairobi. Work includes foundation, wall construction, and plastering.',
                location='Nairobi, Westlands',
                budget=50000,
                duration_days=14
            )
            
            job.required_skills.add(
                Skill.objects.get(name='Masonry'),
                Skill.objects.get(name='Tiling')
            )
            
            # Create a match
            JobMatch.objects.create(
                job_request=job,
                worker=worker,
                match_score=85,
                status='pending'
            )
            
            self.stdout.write(self.style.SUCCESS('Created sample job posting'))
        
        self.stdout.write(self.style.SUCCESS('✅ Data seeding completed successfully!'))