from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

class User(AbstractUser):
    USER_ROLES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    
    role = models.CharField(max_length=10, choices=USER_ROLES, default='student')
    student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    school_email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    class_name = models.CharField(max_length=10, blank=True, null=True)  # For students
    grade = models.IntegerField(null=True, blank=True)  # For students
    subject = models.CharField(max_length=50, blank=True, null=True)  # For teachers
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        super().clean()
        # Skip email domain validation for superusers
        if self.is_superuser:
            return
            
        # Validate email domain for regular users
        if self.email:
            domain = self.email.split('@')[-1]
            allowed_domains = ['buxorobilimdonlar.uz', 'student.buxorobilimdonlar.uz']
            if domain not in allowed_domains:
                raise ValidationError('Email must be from school domain.')
    
    def save(self, *args, **kwargs):
        # Skip clean() validation for superusers
        if not self.is_superuser:
            self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class VerificationRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_requests')
    is_approved = models.BooleanField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"Verification request for {self.user.username}"
