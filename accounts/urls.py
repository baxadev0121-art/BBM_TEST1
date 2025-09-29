from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('verification-requests/', views.verification_requests_view, name='verification_requests'),
    path('approve-verification/<int:request_id>/', views.approve_verification, name='approve_verification'),
    path('reject-verification/<int:request_id>/', views.reject_verification, name='reject_verification'),
]
