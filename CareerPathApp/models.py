from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class StudentProfile(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE)

    name=models.CharField(max_length=50)
    email=models.EmailField()
    phone=models.CharField(max_length=15)

    education=models.CharField(max_length=100)
    skills=models.TextField(blank=True)

    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# assessment
class CareerAssessment(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)

    interest=models.CharField(max_length=100)
    strength=models.CharField(max_length=100)
    work_style=models.CharField(max_length=100)
    career_goal=models.CharField(max_length=200)

    created_goal=models.DateField(auto_now_add=True)

    def __str__(self):
        return self.user.username