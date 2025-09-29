from django.urls import path
from . import views

app_name = 'tests'

urlpatterns = [
    path('', views.test_list_view, name='test_list'),
    path('create/', views.create_test_view, name='create_test'),
    path('<int:test_id>/edit/', views.edit_test_view, name='edit_test'),
    path('<int:test_id>/take/', views.take_test_view, name='take_test'),
    path('attempt/<int:attempt_id>/submit-answer/', views.submit_answer, name='submit_answer'),
    path('attempt/<int:attempt_id>/finish/', views.finish_test, name='finish_test'),
    path('<int:test_id>/results/', views.test_results_view, name='test_results'),
    path('<int:test_id>/info/', views.test_info_view, name='test_info'),
    path('<int:test_id>/export/', views.export_results, name='export_results'),
    path('<int:test_id>/upload-questions/', views.upload_questions, name='upload_questions'),
    path('all-results/', views.all_results_view, name='all_results'),
    # Retake URLs
    path('<int:test_id>/request-retake/', views.request_retake_view, name='request_retake'),
    path('retake-requests/', views.retake_requests_view, name='retake_requests'),
    path('retake-requests/<int:request_id>/handle/', views.handle_retake_request_view, name='handle_retake_request'),
    # Admin student test management
    path('student-management/', views.student_test_management, name='student_test_management'),
    path('<int:test_id>/open-for-student/<int:student_id>/', views.open_test_for_student, name='open_test_for_student'),
]