from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
import json
import pandas as pd
from io import BytesIO
import openpyxl
import random
from .models import Test, Question, Choice, TestAttempt, Answer, TestResult, TestRetakeRequest
from accounts.models import User

@login_required
def test_list_view(request):
    """List all available tests for students or created tests for teachers"""
    if request.method == 'GET' and request.headers.get('Accept') == 'application/json':
        if request.user.role == 'student':
            tests = Test.objects.filter(
                is_active=True,
                grade=request.user.grade
            ).select_related('created_by').order_by('-created_at')
            
            # Add attempt information
            test_data = []
            for test in tests:
                attempt = TestAttempt.objects.filter(test=test, student=request.user).first()
                test_data.append({
                    'id': test.id,
                    'title': test.title,
                    'subject': test.subject,
                    'description': test.description,
                    'grade': test.grade,
                    'time_limit': test.time_limit,
                    'max_attempts': test.max_attempts,
                    'total_questions': test.total_questions,
                    'has_attempted': attempt is not None,
                    'attempt_score': round(attempt.percentage, 1) if attempt and attempt.is_completed else None,
                    'can_attempt': (attempt is None or not attempt.is_completed) and test.is_active,
                    'created_by': test.created_by.get_full_name() or test.created_by.username,
                    'created_at': test.created_at.isoformat(),
                    'start_time': test.start_time.isoformat() if test.start_time else None,
                    'end_time': test.end_time.isoformat() if test.end_time else None,
                })
            
            return JsonResponse({
                'tests': test_data,
                'user_role': 'student'
            })
            
        elif request.user.role == 'teacher':
            tests = Test.objects.filter(created_by=request.user).order_by('-created_at')
            test_data = []
            for test in tests:
                attempt_count = TestAttempt.objects.filter(test=test, is_completed=True).count()
                test_data.append({
                    'id': test.id,
                    'title': test.title,
                    'subject': test.subject,
                    'description': test.description,
                    'grade': test.grade,
                    'total_questions': test.total_questions,
                    'is_active': test.is_active,
                    'created_at': test.created_at.isoformat(),
                    'created_by': test.created_by.get_full_name() or test.created_by.username,
                    'attempt_count': attempt_count,
                    'max_attempts': test.max_attempts,
                    'time_limit': test.time_limit,
                })
            
            return JsonResponse({
                'tests': test_data,
                'user_role': 'teacher'
            })
    
    # Return the HTML template for GET requests
    return render(request, 'tests/test_list.html')

@login_required
@require_http_methods(["POST"])
def create_test(request):
    """Create a new test - Teachers only"""
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['title', 'subject', 'grade', 'time_limit']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'{field} is required'}, status=400)
        
        with transaction.atomic():
            # Create test
            test = Test.objects.create(
                title=data['title'],
                description=data.get('description', ''),
                subject=data['subject'],
                grade=int(data['grade']),
                time_limit=int(data['time_limit']),
                created_by=request.user,
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                max_attempts=data.get('max_attempts', 1),
                show_results=data.get('show_results', True),
                shuffle_questions=data.get('shuffle_questions', False)
            )
            
            # Create questions if provided
            questions_data = data.get('questions', [])
            for i, q_data in enumerate(questions_data):
                question = Question.objects.create(
                    test=test,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    points=float(q_data.get('points', 1.0)),
                    order=i + 1,
                    explanation=q_data.get('explanation', '')
                )
                
                # Create choices for multiple choice questions
                if q_data['question_type'] in ['single_choice', 'multiple_choice']:
                    choices_data = q_data.get('choices', [])
                    for choice_data in choices_data:
                        Choice.objects.create(
                            question=question,
                            choice_text=choice_data['text'],
                            is_correct=choice_data.get('is_correct', False)
                        )
        
        return JsonResponse({
            'message': 'Test created successfully',
            'test_id': test.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def take_test_view(request, test_id):
    """Start or continue taking a test - Students only"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    # Check if student can take this test
    if test.grade != request.user.grade:
        return JsonResponse({'error': 'This test is not for your grade'}, status=403)
    
    # Check time limits
    now = timezone.now()
    if test.start_time and now < test.start_time:
        return JsonResponse({'error': 'Test has not started yet'}, status=403)
    
    if test.end_time and now > test.end_time:
        return JsonResponse({'error': 'Test has ended'}, status=403)
    
    if request.method == 'POST':
        # Start new attempt
        existing_attempt = TestAttempt.objects.filter(test=test, student=request.user).first()
        if existing_attempt and existing_attempt.is_completed:
            return JsonResponse({'error': 'You have already completed this test'}, status=400)
        
        if not existing_attempt:
            attempt = TestAttempt.objects.create(test=test, student=request.user)
        else:
            attempt = existing_attempt
        
        # Get questions
        questions = test.questions.all().order_by('order')
        if test.shuffle_questions:
            questions = questions.order_by('?')
        
        questions_data = []
        for question in questions:
            q_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points
            }
            
            if question.question_type in ['single_choice', 'multiple_choice']:
                q_data['choices'] = [{
                    'id': choice.id,
                    'text': choice.choice_text
                } for choice in question.choices.all()]
            
            questions_data.append(q_data)
        
        return JsonResponse({
            'attempt_id': attempt.id,
            'questions': questions_data,
            'time_limit': test.time_limit,
            'started_at': attempt.started_at.isoformat()
        })
    
    return render(request, 'tests/take_test.html', {'test': test})

@login_required
@require_http_methods(["POST"])
def submit_answer(request, attempt_id):
    """Submit answer for a question"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        attempt = get_object_or_404(TestAttempt, id=attempt_id, student=request.user)
        
        if attempt.is_completed:
            return JsonResponse({'error': 'Test already completed'}, status=400)
        
        question_id = data.get('question_id')
        question = get_object_or_404(Question, id=question_id, test=attempt.test)
        
        # Get or create answer
        answer, created = Answer.objects.get_or_create(
            attempt=attempt,
            question=question
        )
        
        # Clear previous selections
        answer.selected_choices.clear()
        answer.text_answer = ''
        
        # Save new answer based on question type
        if question.question_type == 'text_answer':
            answer.text_answer = data.get('text_answer', '')
        else:
            choice_ids = data.get('choice_ids', [])
            if choice_ids:
                choices = Choice.objects.filter(id__in=choice_ids, question=question)
                answer.selected_choices.set(choices)
        
        answer.save()
        
        return JsonResponse({'message': 'Answer saved'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def finish_test(request, attempt_id):
    """Finish the test and calculate score"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        attempt = get_object_or_404(TestAttempt, id=attempt_id, student=request.user)
        
        if attempt.is_completed:
            return JsonResponse({'error': 'Test already completed'}, status=400)
        
        # Mark attempt as completed
        attempt.finished_at = timezone.now()
        attempt.is_completed = True
        attempt.time_taken = attempt.finished_at - attempt.started_at
        
        # Calculate score
        results = attempt.calculate_score()
        
        # Detailed answer analysis
        correct_answers = 0
        incorrect_answers = 0
        unanswered = 0
        
        for question in attempt.test.questions.all():
            answer = Answer.objects.filter(attempt=attempt, question=question).first()
            if answer:
                if answer.is_correct():
                    correct_answers += 1
                else:
                    incorrect_answers += 1
            else:
                unanswered += 1
        
        # Create test result
        test_result = TestResult.objects.create(
            attempt=attempt,
            correct_answers=correct_answers,
            incorrect_answers=incorrect_answers,
            unanswered=unanswered
        )
        test_result.grade = test_result.calculate_grade()
        test_result.save()
        
        attempt.save()
        
        # Prepare response with completion info
        completion_message = "Test yakunlandi!"
        if results.get('all_answered', False):
            completion_message = f"Ajoyib! Barcha {results['total_questions']} ta savolga javob berdingiz!"
        else:
            completion_message = f"Test yakunlandi. {results['answered_count']}/{results['total_questions']} ta savolga javob berildi."
        
        return JsonResponse({
            'message': completion_message,
            'results': {
                'score': results['score'],
                'total_points': results['total_points'],
                'percentage': results['percentage'],
                'grade': test_result.grade,
                'correct_answers': correct_answers,
                'incorrect_answers': incorrect_answers,
                'unanswered': unanswered,
                'time_taken': str(attempt.time_taken),
                'all_answered': results.get('all_answered', False),
                'answered_count': results.get('answered_count', 0),
                'total_questions': results.get('total_questions', 0),
                'incorrect_questions': results.get('incorrect_questions', [])
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def test_results_view(request, test_id):
    """View test results - Teachers can see all, students see their own"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if it's a JSON request
    if request.headers.get('Accept') == 'application/json':
        if request.user.role == 'student':
            if test.grade != request.user.grade:
                return JsonResponse({'error': 'Access denied'}, status=403)
            
            attempt = TestAttempt.objects.filter(test=test, student=request.user).first()
            if not attempt or not attempt.is_completed:
                return JsonResponse({'error': 'Test not completed'}, status=404)
            
            # Calculate detailed results using the same logic as finish_test
            results = attempt.calculate_score() if hasattr(attempt, 'calculate_score') else {}
            correct_answers = attempt.result.correct_answers if hasattr(attempt, 'result') else 0
            incorrect_answers = attempt.result.incorrect_answers if hasattr(attempt, 'result') else 0
            unanswered = attempt.result.unanswered if hasattr(attempt, 'result') else 0
            result_data = {
                'student': request.user.username,
                'score': attempt.score,
                'total_points': attempt.total_points,
                'percentage': attempt.percentage,
                'grade': attempt.result.grade if hasattr(attempt, 'result') else '',
                'time_taken': str(attempt.time_taken),
                'finished_at': attempt.finished_at.isoformat(),
                'correct_answers': correct_answers,
                'incorrect_answers': incorrect_answers,
                'unanswered': unanswered,
                'all_answered': results.get('all_answered', False),
                'answered_count': results.get('answered_count', 0),
                'total_questions': results.get('total_questions', 0),
                'incorrect_questions': results.get('incorrect_questions', [])
            }
            return JsonResponse({'result': result_data})
        
        elif request.user.role == 'teacher' and test.created_by == request.user:
            # Sinf bo'yicha tartiblab olish
            attempts = TestAttempt.objects.filter(test=test, is_completed=True).select_related('student', 'result').order_by('student__grade', 'student__class_name', 'student__first_name', 'student__last_name')
            
            results_data = []
            for attempt in attempts:
                results_data.append({
                    'student': {
                        'username': attempt.student.username,
                        'first_name': attempt.student.first_name,
                        'last_name': attempt.student.last_name,
                        'student_id': attempt.student.student_id,
                        'class_name': attempt.student.class_name,
                        'grade': attempt.student.grade
                    },
                    'score': attempt.score,
                    'total_points': attempt.total_points,
                    'percentage': attempt.percentage,
                    'grade': attempt.result.grade if hasattr(attempt, 'result') else '',
                    'time_taken': str(attempt.time_taken),
                    'finished_at': attempt.finished_at.isoformat(),
                    'correct_answers': attempt.result.correct_answers if hasattr(attempt, 'result') else 0,
                    'incorrect_answers': attempt.result.incorrect_answers if hasattr(attempt, 'result') else 0
                })
            
            return JsonResponse({'results': results_data})
        
        else:
            return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Return HTML template for regular requests
    return render(request, 'tests/test_results.html', {
        'test': test,
        'user_role': request.user.role
    })

@login_required
def export_results(request, test_id):
    """Export test results to Excel - Teachers only"""
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    # Sinf bo'yicha tartiblab olish
    attempts = TestAttempt.objects.filter(test=test, is_completed=True).select_related('student', 'result').order_by('student__grade', 'student__class_name', 'student__first_name', 'student__last_name')
    
    # Prepare data for Excel
    data = []
    for attempt in attempts:
        data.append({
            'Student Username': attempt.student.username,
            'First Name': attempt.student.first_name,
            'Last Name': attempt.student.last_name,
            'Student ID': attempt.student.student_id or '',
            'Grade': attempt.student.grade or '',
            'Class': attempt.student.class_name or '',
            'Score': attempt.score,
            'Total Points': attempt.total_points,
            'Percentage': attempt.percentage,
            'Grade Result': attempt.result.grade if hasattr(attempt, 'result') else '',
            'Correct Answers': attempt.result.correct_answers if hasattr(attempt, 'result') else 0,
            'Incorrect Answers': attempt.result.incorrect_answers if hasattr(attempt, 'result') else 0,
            'Unanswered': attempt.result.unanswered if hasattr(attempt, 'result') else 0,
            'Time Taken': str(attempt.time_taken),
            'Finished At': attempt.finished_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create Excel file
    df = pd.DataFrame(data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Test Results', index=False)
    
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{test.title}_results.xlsx"'
    
    return response

@login_required
def upload_questions(request, test_id):
    """Upload questions from Excel file - Teachers only"""
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Validate required columns
            required_columns = ['question_text', 'question_type', 'points']
            for col in required_columns:
                if col not in df.columns:
                    return JsonResponse({'error': f'Missing column: {col}'}, status=400)
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    question = Question.objects.create(
                        test=test,
                        question_text=row['question_text'],
                        question_type=row['question_type'],
                        points=float(row.get('points', 1.0)),
                        order=index + 1,
                        explanation=row.get('explanation', '')
                    )
                    
                    # Create choices for multiple choice questions
                    if row['question_type'] in ['single_choice', 'multiple_choice']:
                        for i in range(1, 6):  # Support up to 5 choices
                            choice_col = f'choice_{i}'
                            correct_col = f'choice_{i}_correct'
                            
                            if choice_col in df.columns and pd.notna(row[choice_col]):
                                is_correct = correct_col in df.columns and bool(row[correct_col])
                                Choice.objects.create(
                                    question=question,
                                    choice_text=row[choice_col],
                                    is_correct=is_correct
                                )
            
            return JsonResponse({'message': f'{len(df)} questions uploaded successfully'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return render(request, 'tests/upload_questions.html', {'test': test})

@login_required
def create_test_view(request):
    """Create new test - only for teachers"""
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'GET':
        return render(request, 'tests/create_test.html')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Test yaratish
                test = Test.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description', ''),
                    subject=request.POST.get('subject'),
                    grade=int(request.POST.get('grade')),
                    time_limit=int(request.POST.get('time_limit', 45)),
                    max_attempts=int(request.POST.get('max_attempts', 1)),
                    show_results=bool(request.POST.get('show_results')),
                    is_active=bool(request.POST.get('is_active')),
                    created_by=request.user
                )
                
                # Savollar qo'shish
                question_texts = request.POST.getlist('question_text[]')
                question_types = request.POST.getlist('question_type[]')
                points_list = request.POST.getlist('points[]')
                explanations = request.POST.getlist('explanation[]')
                
                for i, question_text in enumerate(question_texts):
                    if not question_text.strip():
                        continue
                    
                    question = Question.objects.create(
                        test=test,
                        question_text=question_text,
                        question_type=question_types[i],
                        points=float(points_list[i]) if points_list[i] else 1.0,
                        order=i + 1,
                        explanation=explanations[i] if i < len(explanations) else ''
                    )
                    
                    # Javob variantlarini qo'shish
                    if question_types[i] != 'text_answer':
                        choices_key = f'choices_{i+1}[]'
                        correct_key = f'correct_choice_{i+1}'
                        
                        choices = request.POST.getlist(choices_key)
                        correct_index = request.POST.get(correct_key)
                        
                        for j, choice_text in enumerate(choices):
                            if choice_text.strip():
                                is_correct = str(j) == correct_index
                                Choice.objects.create(
                                    question=question,
                                    choice_text=choice_text,
                                    is_correct=is_correct
                                )
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Test muvaffaqiyatli yaratildi!',
                    'test_id': test.id
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def test_info_view(request, test_id):
    """Get test information for display purposes"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check access permissions
    if request.user.role == 'student' and test.grade != request.user.grade:
        return JsonResponse({'error': 'Access denied'}, status=403)
    elif request.user.role == 'teacher' and test.created_by != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    return JsonResponse({
        'title': test.title,
        'description': test.description,
        'subject': test.subject,
        'grade': test.grade,
        'time_limit': test.time_limit,
        'max_attempts': test.max_attempts,
        'total_questions': test.total_questions,
        'created_by': test.created_by.get_full_name() or test.created_by.username,
        'created_at': test.created_at.isoformat(),
        'start_time': test.start_time.isoformat() if test.start_time else None,
        'end_time': test.end_time.isoformat() if test.end_time else None,
    })

@login_required
def all_results_view(request):
    """Barcha test natijalarini ko'rsatish - Admin va Teacher uchun"""
    if request.user.role not in ['admin', 'teacher']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'GET' and request.headers.get('Accept') == 'application/json':
        # Admin barcha natijalarni ko'radi, Teacher faqat o'z testlari natijalarini
        if request.user.role == 'admin':
            attempts = TestAttempt.objects.filter(is_completed=True).select_related(
                'student', 'test', 'result'
            ).order_by('student__grade', 'student__class_name', 'student__first_name', '-finished_at')
        else:  # teacher
            attempts = TestAttempt.objects.filter(
                test__created_by=request.user, 
                is_completed=True
            ).select_related('student', 'test', 'result').order_by(
                'student__grade', 'student__class_name', 'student__first_name', '-finished_at'
            )
        
        results_data = []
        for attempt in attempts:
            # Calculate grade based on percentage
            percentage = attempt.percentage or 0
            if percentage >= 81:
                grade = "A'lo"
            elif percentage >= 61:
                grade = "Yaxshi"
            elif percentage >= 31:
                grade = "Qoniqarli"
            else:
                grade = "Qoniqarsiz"
            results_data.append({
                'test': {
                    'id': attempt.test.id,
                    'title': attempt.test.title,
                    'subject': attempt.test.subject,
                    'grade': attempt.test.grade,
                    'created_by': attempt.test.created_by.get_full_name() or attempt.test.created_by.username
                },
                'student': {
                    'id': attempt.student.id,
                    'username': attempt.student.username,
                    'first_name': attempt.student.first_name,
                    'last_name': attempt.student.last_name,
                    'student_id': attempt.student.student_id,
                    'class_name': attempt.student.class_name,
                    'grade': attempt.student.grade
                },
                'score': attempt.score,
                'total_points': attempt.total_points,
                'percentage': attempt.percentage,
                'grade': grade,
                'time_taken': str(attempt.time_taken),
                'finished_at': attempt.finished_at.isoformat(),
                'correct_answers': attempt.result.correct_answers if hasattr(attempt, 'result') else 0,
                'incorrect_answers': attempt.result.incorrect_answers if hasattr(attempt, 'result') else 0,
                'unanswered': attempt.result.unanswered if hasattr(attempt, 'result') else 0
            })
        
        return JsonResponse({'results': results_data})
    
    return render(request, 'tests/all_results.html', {
        'user_role': request.user.role
    })

@login_required
@require_http_methods(["POST"])
def request_retake_view(request, test_id):
    """O'quvchi qayta ishlash so'rovi yuborish"""
    if request.user.role != 'student':
        return JsonResponse({'error': 'Faqat o\'quvchilar qayta ishlash so\'rovi yuborishi mumkin'}, status=403)
    
    test = get_object_or_404(Test, id=test_id)
    
    try:
        # O'quvchining oxirgi attempt'ini topamiz
        attempt = TestAttempt.objects.filter(test=test, student=request.user, is_completed=True).last()
        if not attempt:
            return JsonResponse({'error': 'Siz hali bu testni topshirmadingiz'}, status=400)
        
        # Qayta ishlash so'rashi mumkinmi?
        if not attempt.can_request_retake():
            return JsonResponse({'error': 'Allaqachon qayta ishlash so\'rovi yuborilgan yoki kutilmoqda'}, status=400)
        
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()
        
        if not reason:
            return JsonResponse({'error': 'Qayta ishlash sababi kiritilishi shart'}, status=400)
        
        # Qayta ishlash so'rovini yaratamiz
        retake_request = TestRetakeRequest.objects.create(
            student=request.user,
            test=test,
            previous_attempt=attempt,
            reason=reason
        )
        
        return JsonResponse({
            'message': 'Qayta ishlash so\'rovi muvaffaqiyatli yuborildi!',
            'request_id': retake_request.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Noto\'g\'ri JSON ma\'lumot'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Xatolik yuz berdi'}, status=500)

@login_required  
def retake_requests_view(request):
    """Admin qayta ishlash so'rovlarini ko'rish va boshqarish"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Faqat adminlar kirishi mumkin'}, status=403)
    
    if request.method == 'GET' and request.headers.get('Accept') == 'application/json':
        # JSON API so'rovi
        status_filter = request.GET.get('status', 'all')
        
        requests_qs = TestRetakeRequest.objects.select_related(
            'student', 'test', 'previous_attempt', 'approved_by'
        ).order_by('-created_at')
        
        if status_filter != 'all':
            requests_qs = requests_qs.filter(status=status_filter)
        
        requests_data = []
        for req in requests_qs:
            requests_data.append({
                'id': req.id,
                'student_name': req.student.get_full_name(),
                'student_username': req.student.username,
                'student_grade': req.student.grade,
                'student_class': req.student.class_name,
                'test_title': req.test.title,
                'test_subject': req.test.subject,
                'previous_score': req.previous_attempt.score,
                'previous_percentage': req.previous_attempt.percentage,
                'reason': req.reason,
                'status': req.status,
                'status_display': req.get_status_display(),
                'admin_response': req.admin_response,
                'approved_by': req.approved_by.get_full_name() if req.approved_by else None,
                'created_at': req.created_at.isoformat(),
                'updated_at': req.updated_at.isoformat()
            })
        
        return JsonResponse({
            'requests': requests_data,
            'total_count': len(requests_data)
        })
    
    # HTML template
    return render(request, 'tests/retake_requests.html')

@login_required
@require_http_methods(["POST"])
def handle_retake_request_view(request, request_id):
    """Admin qayta ishlash so'rovini tasdiqlash yoki rad etish"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Faqat adminlar kirishi mumkin'}, status=403)
    
    retake_request = get_object_or_404(TestRetakeRequest, id=request_id)
    
    if retake_request.status != 'pending':
        return JsonResponse({'error': 'Bu so\'rov allaqachon ko\'rib chiqilgan'}, status=400)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'approve' yoki 'reject'
        admin_response = data.get('admin_response', '').strip()
        
        if action not in ['approve', 'reject']:
            return JsonResponse({'error': 'Noto\'g\'ri harakat'}, status=400)
        
        retake_request.status = 'approved' if action == 'approve' else 'rejected'
        retake_request.admin_response = admin_response
        retake_request.approved_by = request.user
        retake_request.save()
        
        return JsonResponse({
            'message': f'So\'rov {"tasdiqlandi" if action == "approve" else "rad etildi"}!',
            'status': retake_request.status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Noto\'g\'ri JSON ma\'lumot'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Xatolik yuz berdi'}, status=500)


@login_required
def open_test_for_student(request, test_id, student_id):
    """Admin tomonidan o'quvchi uchun testni qayta ochish"""
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Ruxsat berilmagan'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST so\'rov talab qilinadi'}, status=405)
    
    try:
        test = Test.objects.get(id=test_id)
        student = User.objects.get(id=student_id, role='student')
        
        # O'quvchining bu testdagi avvalgi urinishlarini tekshirish
        previous_attempts = TestAttempt.objects.filter(
            student=student,
            test=test
        ).count()
        
        # Yangi urinish yaratish (qayta ishlash imkoniyati)
        new_attempt = TestAttempt.objects.create(
            student=student,
            test=test,
            attempt_number=previous_attempts + 1,
            is_retake=True
        )
        
        # Agar qayta ishlash so'rovi mavjud bo'lsa, uni tasdiqlangan deb belgilash
        retake_request = TestRetakeRequest.objects.filter(
            student=student,
            test=test,
            status='approved'
        ).first()
        
        if retake_request:
            retake_request.is_used = True
            retake_request.save()
        
        return JsonResponse({
            'message': f'{student.get_full_name()} uchun "{test.title}" testi qayta ochildi!',
            'attempt_id': new_attempt.id,
            'attempt_number': new_attempt.attempt_number
        })
        
    except Test.DoesNotExist:
        return JsonResponse({'error': 'Test topilmadi'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'error': 'O\'quvchi topilmadi'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def student_test_management(request):
    """Admin uchun o'quvchilarning test holatlarini boshqarish"""
    if request.user.role != 'admin':
        return redirect('accounts:dashboard')
    
    # Barcha faol testlar
    tests = Test.objects.filter(is_active=True)
    
    # Barcha tasdiqlangan o'quvchilar
    students = User.objects.filter(role='student', is_verified=True)
    
    # Har bir o'quvchi va test uchun urinishlar ma'lumotlari
    student_test_data = []
    
    for student in students:
        student_tests = []
        for test in tests:
            attempts = TestAttempt.objects.filter(student=student, test=test)
            latest_attempt = attempts.order_by('-started_at').first()
            
            # Qayta ishlash so'rovlari
            retake_requests = TestRetakeRequest.objects.filter(
                student=student,
                test=test
            ).order_by('-created_at')
            
            test_info = {
                'test': test,
                'attempts_count': attempts.count(),
                'latest_attempt': latest_attempt,
                'can_retake': latest_attempt is not None,
                'retake_requests': retake_requests
            }
            student_tests.append(test_info)
        
        student_test_data.append({
            'student': student,
            'tests': student_tests
        })
    
    context = {
        'student_test_data': student_test_data,
        'all_tests': tests
    }
    
    return render(request, 'tests/student_test_management.html', context)

@login_required
def edit_test_view(request, test_id):
    """Edit an existing test and its questions (teachers only)"""
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    if request.user.role != 'teacher':
        return JsonResponse({'error': 'Access denied'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Update test fields
            test.title = data.get('title', test.title)
            test.description = data.get('description', test.description)
            test.subject = data.get('subject', test.subject)
            test.grade = int(data.get('grade', test.grade))
            test.time_limit = int(data.get('time_limit', test.time_limit))
            test.max_attempts = int(data.get('max_attempts', test.max_attempts))
            test.show_results = data.get('show_results', test.show_results)
            test.is_active = data.get('is_active', test.is_active)
            test.save()

            # Update questions
            questions_data = data.get('questions', [])
            # Remove old questions not in new data
            new_ids = [q.get('id') for q in questions_data if q.get('id')]
            test.questions.exclude(id__in=new_ids).delete()
            for i, q_data in enumerate(questions_data):
                if q_data.get('id'):
                    # Update existing question
                    question = Question.objects.get(id=q_data['id'], test=test)
                    question.question_text = q_data['question_text']
                    question.question_type = q_data['question_type']
                    question.points = float(q_data.get('points', 1.0))
                    question.order = i + 1
                    question.explanation = q_data.get('explanation', '')
                    question.save()
                    # Update choices
                    if q_data['question_type'] in ['single_choice', 'multiple_choice']:
                        choices_data = q_data.get('choices', [])
                        new_choice_ids = [c.get('id') for c in choices_data if c.get('id')]
                        question.choices.exclude(id__in=new_choice_ids).delete()
                        for c_data in choices_data:
                            if c_data.get('id'):
                                choice = Choice.objects.get(id=c_data['id'], question=question)
                                choice.choice_text = c_data['text']
                                choice.is_correct = c_data.get('is_correct', False)
                                choice.save()
                            else:
                                Choice.objects.create(
                                    question=question,
                                    choice_text=c_data['text'],
                                    is_correct=c_data.get('is_correct', False)
                                )
                    else:
                        question.choices.all().delete()
                else:
                    # Create new question
                    question = Question.objects.create(
                        test=test,
                        question_text=q_data['question_text'],
                        question_type=q_data['question_type'],
                        points=float(q_data.get('points', 1.0)),
                        order=i + 1,
                        explanation=q_data.get('explanation', '')
                    )
                    if q_data['question_type'] in ['single_choice', 'multiple_choice']:
                        for c_data in q_data.get('choices', []):
                            Choice.objects.create(
                                question=question,
                                choice_text=c_data['text'],
                                is_correct=c_data.get('is_correct', False)
                            )
            # Saqlangan savollarni JSON ko‘rinishda qaytarish:
            questions = test.questions.all().order_by('order')
            questions_data = []
            for q in questions:
                q_data = {
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "points": q.points,
                    "explanation": q.explanation,
                    "choices": [
                        {"text": c.choice_text, "is_correct": c.is_correct}
                        for c in q.choices.all()
                    ]
                }
                questions_data.append(q_data)
            return JsonResponse({"success": True, "questions": questions_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # GET: Render edit page with test and questions
    questions = test.questions.all().order_by('order')
    questions_data = []
    for q in questions:
        q_data = {
            'id': q.id,
            'question_text': q.question_text,
            'question_type': q.question_type,
            'points': q.points,
            'explanation': q.explanation,
            'choices': []
        }
        if q.question_type in ['single_choice', 'multiple_choice']:
            q_data['choices'] = [
                {'id': c.id, 'text': c.choice_text, 'is_correct': c.is_correct}
                for c in q.choices.all()
            ]
        questions_data.append(q_data)
    context = {
        'test': test,
        'questions': questions_data
    }
    return render(request, 'tests/edit_test.html', context)

@login_required
def start_test_view(request, test_id):
    """Admin tomonidan o'quvchi uchun testi boshlash"""
    test = get_object_or_404(Test, pk=test_id)
    questions = list(test.questions.all())
    random.shuffle(questions)  # Har bir o‘quvchi uchun random tartib
    
    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'tests/start_test.html', context)
