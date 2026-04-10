from django.db import models

class HeroBanner(models.Model):
    """Model for hero section banners/sliders"""
    title = models.CharField(max_length=200, blank=True, help_text="Optional title for this banner")
    subtitle = models.CharField(max_length=200, blank=True, help_text="Optional subtitle")
    image = models.ImageField(upload_to='hero_banners/', help_text="Banner image (recommended size: 1920x800)")
    alt_text = models.CharField(max_length=100, blank=True, help_text="Alt text for accessibility")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    is_active = models.BooleanField(default=True, help_text="Show this banner on the homepage")
    link_url = models.CharField(max_length=200, blank=True, help_text="Optional link URL when clicked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Hero Banner"
        verbose_name_plural = "Hero Banners"
    
    def __str__(self):
        return self.title or f"Banner {self.id}"

class FeatureImage(models.Model):
    """Model for feature section images"""
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='feature_images/', help_text="Feature image (recommended size: 400x300)")
    alt_text = models.CharField(max_length=100, blank=True)
    code_example = models.CharField(max_length=100, blank=True, help_text="Code example like 'JOBS' or 'ADD_SKILL'")
    code_description = models.CharField(max_length=200, blank=True, help_text="Description of the code")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Feature Image"
        verbose_name_plural = "Feature Images"
    
    def __str__(self):
        return self.title