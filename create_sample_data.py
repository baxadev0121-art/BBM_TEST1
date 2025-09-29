#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mytest.settings')
django.setup()

from accounts.models import User, VerificationRequest
from tests_app.models import Test, Question, Choice

def create_sample_data():
    print("Creating sample data...")
    
    # Create sample teacher
    teacher, created = User.objects.get_or_create(
        username='teacher1',
        defaults={
            'email': 'teacher@buxorobilimdonlar.uz',
            'first_name': 'Nodira',
            'last_name': 'Karimova',
            'role': 'teacher',
            'subject': 'Matematika',
            'is_verified': True,
        }
    )
    if created:
        teacher.set_password('teacher123')
        teacher.save()
        print(f"✓ Created teacher: {teacher.username}")
    
    # Create sample student
    student, created = User.objects.get_or_create(
        username='student1',
        defaults={
            'email': 'student@student.buxorobilimdonlar.uz',
            'first_name': 'Ali',
            'last_name': 'Valiyev',
            'role': 'student',
            'student_id': 'STU001',
            'grade': 9,
            'class_name': '9-A',
            'is_verified': True,
        }
    )
    if created:
        student.set_password('student123')
        student.save()
        print(f"✓ Created student: {student.username}")
    
    # Create unverified student for testing
    unverified_student, created = User.objects.get_or_create(
        username='student2',
        defaults={
            'email': 'student2@student.buxorobilimdonlar.uz',
            'first_name': 'Malika',
            'last_name': 'Rahimova',
            'role': 'student',
            'student_id': 'STU002',
            'grade': 10,
            'class_name': '10-B',
            'is_verified': False,
        }
    )
    if created:
        unverified_student.set_password('student123')
        unverified_student.save()
        print(f"✓ Created unverified student: {unverified_student.username}")
        
        # Create verification request
        VerificationRequest.objects.get_or_create(user=unverified_student)
        print(f"✓ Created verification request for {unverified_student.username}")
    
    # Create sample test
    test, created = Test.objects.get_or_create(
        title='Matematika - Algebraik ifodalar',
        defaults={
            'description': '9-sinf uchun algebraik ifodalar mavzusida test',
            'subject': 'Matematika',
            'grade': 9,
            'created_by': teacher,
            'time_limit': 45,
            'is_active': True,
            'max_attempts': 1,
            'show_results': True,
        }
    )
    
    if created:
        print(f"✓ Created test: {test.title}")
        
        # Create sample questions
        questions_data = [
            {
                'question_text': 'Quyidagi algebraik ifodani soddalashtirig: 3x + 2x - x',
                'question_type': 'single_choice',
                'points': 2.0,
                'choices': [
                    {'text': '4x', 'is_correct': True},
                    {'text': '5x', 'is_correct': False},
                    {'text': '6x', 'is_correct': False},
                    {'text': '3x', 'is_correct': False},
                ]
            },
            {
                'question_text': 'Agar x = 2 bo\'lsa, 3x² - 2x + 1 ifodaning qiymati qanchaga teng?',
                'question_type': 'single_choice',
                'points': 3.0,
                'choices': [
                    {'text': '9', 'is_correct': True},
                    {'text': '11', 'is_correct': False},
                    {'text': '7', 'is_correct': False},
                    {'text': '13', 'is_correct': False},
                ]
            },
            {
                'question_text': 'Quyidagi qaysi ifodalar bir-biriga teng? (Bir nechta javob bo\'lishi mumkin)',
                'question_type': 'multiple_choice',
                'points': 4.0,
                'choices': [
                    {'text': '2(x + 3)', 'is_correct': True},
                    {'text': '2x + 6', 'is_correct': True},
                    {'text': '2x + 3', 'is_correct': False},
                    {'text': 'x + x + 6', 'is_correct': True},
                ]
            },
            {
                'question_text': 'Algebraik ifoda nima? Qisqacha tushuntiring.',
                'question_type': 'text_answer',
                'points': 5.0,
                'explanation': 'Algebraik ifoda - sonlar, harflar va amallar belgilaridan iborat matematik ifoda'
            }
        ]
        
        for i, q_data in enumerate(questions_data, 1):
            question = Question.objects.create(
                test=test,
                question_text=q_data['question_text'],
                question_type=q_data['question_type'],
                points=q_data['points'],
                order=i,
                explanation=q_data.get('explanation', '')
            )
            
            if 'choices' in q_data:
                for choice_data in q_data['choices']:
                    Choice.objects.create(
                        question=question,
                        choice_text=choice_data['text'],
                        is_correct=choice_data['is_correct']
                    )
            
            print(f"  ✓ Created question {i}: {question.question_text[:50]}...")
    
    # Create another test for 10th grade
    test2, created = Test.objects.get_or_create(
        title='Matematika - Tengsizliklar',
        defaults={
            'description': '10-sinf uchun tengsizliklar mavzusida test',
            'subject': 'Matematika',
            'grade': 10,
            'created_by': teacher,
            'time_limit': 60,
            'is_active': True,
            'max_attempts': 2,
            'show_results': True,
        }
    )
    
    if created:
        print(f"✓ Created test: {test2.title}")
        
        # Create sample questions for second test
        question1 = Question.objects.create(
            test=test2,
            question_text='x > 5 tengsizlikni intervallar usulida yozing',
            question_type='single_choice',
            points=3.0,
            order=1
        )
        
        choices = [
            {'text': '(5; +∞)', 'is_correct': True},
            {'text': '[5; +∞)', 'is_correct': False},
            {'text': '(-∞; 5)', 'is_correct': False},
            {'text': '(-∞; 5]', 'is_correct': False},
        ]
        
        for choice_data in choices:
            Choice.objects.create(
                question=question1,
                choice_text=choice_data['text'],
                is_correct=choice_data['is_correct']
            )
        
        print(f"  ✓ Created question for second test")
    
    print("\n🎉 Sample data created successfully!")
    print("\nLogin credentials:")
    print("Admin: admin / admin123")
    print("Teacher: teacher1 / teacher123")
    print("Student: student1 / student123")
    print("Unverified Student: student2 / student123")
    print(f"\nServer URL: http://localhost:8000")

if __name__ == '__main__':
    create_sample_data()
