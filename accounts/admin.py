from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import User, VerificationRequest

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'is_verified', 'school_email_verified', 'student_id', 'is_active']
    list_filter = ['role', 'is_verified', 'school_email_verified', 'is_active', 'grade']
    search_fields = ['username', 'email', 'student_id', 'first_name', 'last_name']
    
    fieldsets = UserAdmin.fieldsets + (
        ('School Info', {
            'fields': ('role', 'student_id', 'is_verified', 'school_email_verified', 
                      'phone_number', 'class_name', 'grade', 'subject')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('School Info', {
            'fields': ('role', 'student_id', 'email', 'phone_number', 'class_name', 'grade', 'subject')
        }),
    )

@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'requested_at', 'is_approved', 'processed_by', 'processed_at']
    list_filter = ['is_approved', 'requested_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['requested_at']
    
    def approve_request(self, request, queryset):
        for verification_request in queryset:
            verification_request.user.is_verified = True
            verification_request.user.save()
            verification_request.is_approved = True
            verification_request.processed_by = request.user
            verification_request.processed_at = timezone.now()
            verification_request.save()
        self.message_user(request, f'{queryset.count()} requests approved.')
    
    def reject_request(self, request, queryset):
        for verification_request in queryset:
            verification_request.is_approved = False
            verification_request.processed_by = request.user
            verification_request.processed_at = timezone.now()
            verification_request.save()
        self.message_user(request, f'{queryset.count()} requests rejected.')
    
    approve_request.short_description = "Approve selected requests"
    reject_request.short_description = "Reject selected requests"
    actions = [approve_request, reject_request]

admin.site.register(User, CustomUserAdmin)
