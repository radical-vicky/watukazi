from django.contrib import admin
from .models import EmployerProfile

@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'total_jobs_posted', 'rating', 'is_verified_business')
    search_fields = ('user__username', 'company_name')