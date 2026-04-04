from django.contrib import admin
from .models import Skill, WorkerProfile, SkillCategory

@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'availability_status', 'rating', 'total_jobs_completed')
    list_filter = ('availability_status',)
    search_fields = ('user__username', 'user__profile__phone_number')