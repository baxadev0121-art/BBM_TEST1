from django.db import models
from django.conf import settings
import json
from django.utils import timezone

class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100)
    grade = models.IntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tests')
    time_limit = models.IntegerField(help_text="Time limit in minutes")
    is_active = models.BooleanField(default=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    max_attempts = models.IntegerField(default=1)
    show_results = models.BooleanField(default=True)
    shuffle_questions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    @property
    def total_questions(self):
        return self.questions.count()
    
    @property
    def total_points(self):
        return sum(question.points for question in self.questions.all())

class Question(models.Model):
    QUESTION_TYPES = (
        ('single_choice', 'Single Choice'),
        ('multiple_choice', 'Multiple Choice'),
        ('text_answer', 'Text Answer'),
    )
    
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=15, choices=QUESTION_TYPES)
    points = models.FloatField(default=1.0)
    order = models.IntegerField(default=0)
    explanation = models.TextField(blank=True, help_text="Explanation for the correct answer")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.test.title} - Q{self.order}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.question} - {self.choice_text[:50]}"

class TestAttempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    total_points = models.FloatField(default=0)
    percentage = models.FloatField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    time_taken = models.DurationField(null=True, blank=True)
    attempt_number = models.IntegerField(default=1)  # Qayta ishlash raqami
    is_retake = models.BooleanField(default=False)  # Qayta ishlashmi
    
    class Meta:
        ordering = ['-started_at']
    
    def can_request_retake(self):
        """O'quvchi qayta ishlash so'rashi mumkinmi?"""
        if not self.is_completed:
            return False
        # Allaqachon so'ralgan va kutilayotgan retake bormi?
        from tests_app.models import TestRetakeRequest
        pending_request = TestRetakeRequest.objects.filter(
            student=self.student,
            test=self.test,
            previous_attempt=self,
            status='pending'
        ).exists()
        return not pending_request
    
    def calculate_score(self):
        total_points = 0
        earned_points = 0
        total_questions = self.test.questions.count()
        answered_questions = self.answers.count()
        
        # Barcha savollarga javob berilganligini tekshirish
        all_questions_answered = answered_questions == total_questions
        
        # Har bir savol uchun ballni hisoblash
        incorrect_questions = []
        for question in self.test.questions.all():
            total_points += question.points
            
            # Bu savolga javob berilganmi?
            answer = self.answers.filter(question=question).first()
            if answer and answer.is_correct():
                earned_points += question.points
            elif answer:
                correct_choice = question.choices.filter(is_correct=True).first()
                incorrect_questions.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'answer': answer.selected_choices.first().choice_text if answer.selected_choices.exists() else answer.text_answer,
                    'correct_answer': correct_choice.choice_text if correct_choice else None
                })
            else:
                correct_choice = question.choices.filter(is_correct=True).first()
                incorrect_questions.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'answer': None,
                    'correct_answer': correct_choice.choice_text if correct_choice else None
                })
        
        # Agar barcha savollarga javob berilgan bo'lsa, bonus ball qo'shish mumkin
        if all_questions_answered:
            # Bonus ball: agar barcha savollarga javob berilgan bo'lsa, 
            # noto'g'ri javoblar ham hisobga olinadi
            completion_bonus = 0  # Hozircha bonus yo'q, faqat to'g'ri javoblar hisoblanadi
        else:
            # Agar barcha savollarga javob berilmagan bo'lsa, jarimaga solish
            completion_bonus = 0
        
        final_score = earned_points + completion_bonus
        
        self.score = final_score
        self.total_points = total_points
        self.percentage = (final_score / total_points * 100) if total_points > 0 else 0
        self.save()
        
        return {
            'score': self.score,
            'total_points': self.total_points,
            'percentage': self.percentage,
            'all_answered': all_questions_answered,
            'answered_count': answered_questions,
            'total_questions': total_questions,
            'incorrect_questions': incorrect_questions
        }
    
    def __str__(self):
        return f"{self.student.username} - {self.test.title}"

class Answer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(auto_now=True)
    
    def is_correct(self):
        if self.question.question_type == 'text_answer':
            # For text answers, teacher needs to grade manually
            return False  # Can be updated later with manual grading
        
        elif self.question.question_type == 'single_choice':
            selected = self.selected_choices.first()
            return selected and selected.is_correct
        
        elif self.question.question_type == 'multiple_choice':
            correct_choices = set(self.question.choices.filter(is_correct=True))
            selected_choices = set(self.selected_choices.all())
            return correct_choices == selected_choices
        
        return False
    
    def __str__(self):
        return f"{self.attempt.student.username} - {self.question}"

class TestResult(models.Model):
    attempt = models.OneToOneField(TestAttempt, on_delete=models.CASCADE, related_name='result')
    correct_answers = models.IntegerField(default=0)
    incorrect_answers = models.IntegerField(default=0)
    unanswered = models.IntegerField(default=0)
    grade = models.CharField(max_length=15, blank=True)  # A'lo, Yaxshi, Qoniqarli, Qoniqarsiz
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def calculate_grade(self):
        percentage = self.attempt.percentage
        if percentage >= 81:
            return "A'lo"
        elif percentage >= 61:
            return 'Yaxshi'
        elif percentage >= 31:
            return 'Qoniqarli'
        else:
            return 'Qoniqarsiz'
    
    def __str__(self):
        return f"Result for {self.attempt}"

class TestRetakeRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
    )
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='retake_requests')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='retake_requests')
    previous_attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='retake_requests')
    reason = models.TextField(help_text="Qayta ishlash sababi")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_response = models.TextField(blank=True, help_text="Admin javobi")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_retakes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_used = models.BooleanField(default=False, help_text="Qayta ishlash so'rovi ishlatilganmi")
    
    class Meta:
        unique_together = ['student', 'test', 'previous_attempt']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.test.title} - {self.get_status_display()}"
