from django.db import models
from django.contrib.auth.models import User


class Subject(models.TextChoices):
    MATEMATIK = "MAT", "Matematik"
    FIZIK = "FIZ", "Fizik"
    KIMYA = "KIM", "Kimya"
    BIYOLOJI = "BIO", "Biyoloji"
    GEOMETRI = "GEO", "Geometri"


class Difficulty(models.TextChoices):
    EASY = "E", "Kolay"
    MEDIUM = "M", "Orta"
    HARD = "H", "Zor"


class Topic(models.Model):
    subject = models.CharField(max_length=3, choices=Subject.choices)
    name = models.CharField(max_length=120)
    def __str__(self): return f"{self.get_subject_display()} - {self.name}"


class Question(models.Model):
    subject = models.CharField(max_length=3, choices=Subject.choices)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.CharField(max_length=1, choices=Difficulty.choices)
    stem = models.TextField() # soru kökü
    choices = models.JSONField(default=list) # ["A) ...","B) ...",...]
    answer = models.CharField(max_length=1) # "A".."E"
    rubric = models.TextField(blank=True, default="") # çözüm
    source = models.CharField(max_length=120, blank=True, default="ai")
    created_at = models.DateTimeField(auto_now_add=True)


class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.CharField(max_length=1)
    correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)