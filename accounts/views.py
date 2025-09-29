from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User, VerificationRequest
import json

def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['username', 'email', 'password', 'role']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'error': f'{field} is required'}, status=400)
            
            # Check if user exists
            if User.objects.filter(username=data['username']).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)
            
            if User.objects.filter(email=data['email']).exists():
                return JsonResponse({'error': 'Email already exists'}, status=400)
            
            # Validate email domain
            email_domain = data['email'].split('@')[-1]
            allowed_domains = ['buxorobilimdonlar.uz', 'student.buxorobilimdonlar.uz']
            if email_domain not in allowed_domains:
                return JsonResponse({'error': 'Email must be from school domain'}, status=400)
            
            # Create user
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                role=data['role']
            )
            
            # Set additional fields based on role
            if data['role'] == 'student':
                user.student_id = data.get('student_id')
                user.class_name = data.get('class_name')
                user.grade = data.get('grade')
            elif data['role'] == 'teacher':
                user.subject = data.get('subject')
            
            user.phone_number = data.get('phone_number')
            user.save()
            
            # Create verification request
            VerificationRequest.objects.create(user=user)
            
            return JsonResponse({
                'message': 'Account created successfully. Please wait for admin approval.',
                'user_id': user.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred during registration'}, status=500)
    
    return render(request, 'accounts/signup.html')

def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username_or_email = data.get('username')
            password = data.get('password')
            
            if not username_or_email or not password:
                return JsonResponse({'error': 'Username/Email and password are required'}, status=400)
            
            # Try to authenticate with username first
            user = authenticate(request, username=username_or_email, password=password)
            
            # If that fails, try to find user by email and authenticate
            if user is None:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                if not user.is_verified:
                    return JsonResponse({'error': 'Account not verified yet. Please wait for admin approval.'}, status=403)
                
                login(request, user)
                return JsonResponse({
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'email': user.email,
                        'is_verified': user.is_verified
                    }
                })
            else:
                return JsonResponse({'error': 'Invalid username/email or password'}, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred during login'}, status=500)
    
    return render(request, 'accounts/login.html')

@login_required
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

@login_required
def dashboard_view(request):
    from tests_app.models import TestResult, TestAttempt, Test
    
    context = {
        'user': request.user,
        'verification_requests_count': 0
    }
    
    if request.user.role == 'admin':
        context['verification_requests_count'] = VerificationRequest.objects.filter(is_approved=None).count()
    elif request.user.role == 'student':
        # O'quvchi uchun natijalarni olish
        test_results = TestResult.objects.filter(
            attempt__student=request.user
        ).select_related('attempt', 'attempt__test').order_by('-attempt__started_at')[:5]
        
        context['recent_results'] = []
        for result in test_results:
            # Grade ni hisoblash
            percentage = (result.attempt.score / result.attempt.total_points * 100) if result.attempt.total_points > 0 else 0
            if percentage >= 81:
                grade = "A'lo"
            elif percentage >= 61:
                grade = 'Yaxshi'
            elif percentage >= 31:
                grade = 'Qoniqarli'
            else:
                grade = 'Qoniqarsiz'
                
            context['recent_results'].append({
                'test_name': result.attempt.test.title,
                'score': result.attempt.score,
                'max_score': result.attempt.total_points,
                'percentage': percentage,
                'grade': grade,
                'created_at': result.attempt.started_at,
                'test_id': result.attempt.test.id
            })
        
        # Umumiy statistika
        all_results = TestResult.objects.filter(attempt__student=request.user)
        context['total_tests'] = all_results.count()
        
        if all_results:
            total_percentage = sum([
                (r.attempt.score / r.attempt.total_points * 100) if r.attempt.total_points > 0 else 0 
                for r in all_results
            ])
            context['average_score'] = total_percentage / len(all_results) if all_results else 0
            
            # Eng yaxshi natija
            best_result = max(all_results, key=lambda x: (x.attempt.score/x.attempt.total_points*100) if x.attempt.total_points > 0 else 0)
            best_percentage = (best_result.attempt.score / best_result.attempt.total_points * 100) if best_result.attempt.total_points > 0 else 0
            
            # Grade ni hisoblash
            if best_percentage >= 81:
                best_grade = "A'lo"
            elif best_percentage >= 61:
                best_grade = 'Yaxshi'
            elif best_percentage >= 31:
                best_grade = 'Qoniqarli'
            else:
                best_grade = 'Qoniqarsiz'
                
            context['best_result'] = {
                'test_name': best_result.attempt.test.title,
                'score': best_result.attempt.score,
                'max_score': best_result.attempt.total_points,
                'percentage': best_percentage,
                'grade': best_grade
            }
        else:
            context['average_score'] = 0
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def profile_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = request.user
            
            # Update allowed fields
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.phone_number = data.get('phone_number', user.phone_number)
            
            if user.role == 'student':
                user.class_name = data.get('class_name', user.class_name)
            elif user.role == 'teacher':
                user.subject = data.get('subject', user.subject)
            
            user.save()
            
            return JsonResponse({'message': 'Profile updated successfully'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred'}, status=500)
    
    return render(request, 'accounts/profile.html')

@login_required
def verification_requests_view(request):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'GET' and request.headers.get('Accept') == 'application/json':
        # Sinf bo'yicha tartiblab olish
        requests = VerificationRequest.objects.filter(is_approved=None).select_related('user').order_by('user__grade', 'user__class_name', 'user__first_name')
        requests_data = [{
            'id': req.id,
            'user': {
                'id': req.user.id,
                'username': req.user.username,
                'email': req.user.email,
                'first_name': req.user.first_name,
                'last_name': req.user.last_name,
                'role': req.user.role,
                'student_id': req.user.student_id,
                'class_name': req.user.class_name,
                'grade': req.user.grade,
                'subject': req.user.subject,
            },
            'requested_at': req.requested_at.isoformat()
        } for req in requests]
        
        return JsonResponse({'requests': requests_data})
    
    return render(request, 'accounts/verification_requests.html')

@login_required
@require_http_methods(["POST"])
def approve_verification(request, request_id):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        verification_request = VerificationRequest.objects.get(id=request_id)
        verification_request.is_approved = True
        verification_request.processed_by = request.user
        verification_request.processed_at = timezone.now()
        verification_request.save()
        
        # Verify the user
        verification_request.user.is_verified = True
        verification_request.user.save()
        
        return JsonResponse({'message': 'User verified successfully'})
    
    except VerificationRequest.DoesNotExist:
        return JsonResponse({'error': 'Verification request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'An error occurred'}, status=500)

@login_required
@require_http_methods(["POST"])
def reject_verification(request, request_id):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        verification_request = VerificationRequest.objects.get(id=request_id)
        verification_request.is_approved = False
        verification_request.processed_by = request.user
        verification_request.processed_at = timezone.now()
        verification_request.rejection_reason = data.get('reason', '')
        verification_request.save()
        
        return JsonResponse({'message': 'Verification request rejected'})
    
    except VerificationRequest.DoesNotExist:
        return JsonResponse({'error': 'Verification request not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'An error occurred'}, status=500)
