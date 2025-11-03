from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path("questions/generate/", views.generate_question, name='generate-question'),
    path("questions/<int:pk>/explain/", views.explain, name='explain-question'),
    path("questions/stats/", views.question_stats, name='question-stats'),
    path("questions/cleanup/", views.cleanup_questions, name='cleanup-questions'),
]
