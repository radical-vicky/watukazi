from django.contrib import admin
from .models import HeroBanner, FeatureImage

@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'alt_text']
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'image', 'alt_text', 'link_url')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )

@admin.register(FeatureImage)
class FeatureImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'image', 'alt_text')
        }),
        ('Code Display', {
            'fields': ('code_example', 'code_description')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )