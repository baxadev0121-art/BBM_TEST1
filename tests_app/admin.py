from django.contrib import admin
from .models import Test, Question, Choice, TestAttempt, Answer, TestResult

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['test', 'question_text', 'question_type', 'points', 'order']
    list_filter = ['question_type', 'test__subject']
    search_fields = ['question_text', 'test__title']
    inlines = [ChoiceInline]
    list_editable = ['points', 'order']

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'grade', 'created_by', 'is_active', 'time_limit', 'total_questions']
    list_filter = ['subject', 'grade', 'is_active', 'created_by']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]
    readonly_fields = ['total_questions', 'total_points']

@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'test', 'started_at', 'finished_at', 'score', 'percentage', 'is_completed']
    list_filter = ['is_completed', 'test__subject', 'started_at']
    search_fields = ['student__username', 'test__title']
    readonly_fields = ['started_at', 'score', 'percentage', 'time_taken']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'is_correct', 'answered_at']
    list_filter = ['question__question_type', 'answered_at']
    search_fields = ['attempt__student__username', 'question__question_text']

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'correct_answers', 'incorrect_answers', 'grade', 'created_at']
    list_filter = ['grade', 'created_at']
    search_fields = ['attempt__student__username', 'attempt__test__title']
