
from django.urls import path
from . import views
from .views import*
urlpatterns = [
   path("",views.home,name='home'),
   path('register/',views.register,name='register'),
   path('student_profile/',views.student_profile,name='student_profile'),
   path('career_assessment/',views.career_assessment,name='career_assessment'),
   path('career_match/',views.career_match,name='career_match'),
   path('explore_careers/',views.explore_careers,name='explore_careers'),
   path('login/',views.user_login,name='login'),
   path('career_details/<slug:career_name>/',views.career_details,name='career_details'),
   path('career_roadmap/<slug:career_name>/',views.career_roadmap,name='career_roadmap'),
   path('about/',views.about,name='about'),
   path('work/',views.work,name='work'),
   path('contact/',views.contact,name='contact'),
   path('career-chatbot/',views.career_chatbot,name='career_chatbot'),
   path( "chatbot-api/",views.chatbot_api,name="chatbot_api"),
   path('mock-interview/',views.mock_interview,name='mock_interview'),
   path('mock-interview/api/',views.mock_interview_api,name='mock_interview_api'),
   path("career-aptitude-api/",career_aptitude_api,name="career_aptitude_api"),
   path("career-aptitude/",career_aptitude_quiz,name='career_aptitude_quiz'),
   path("job-internship-recommendation/",views.job_internship_recommendation,name='job_internship_recommendation'),
   path("job-internship-analysis/",views.job_internship_analysis,name="job_internship_analysis"),
   path("job-internship-analysis-api/",views.job_internship_analysis_api,name="job_internship_analysis_api"),
   path("job-internship-recommendation-api/",views.job_internship_recommendation,name="job_internship_recommendation_api"),
   path("job-internship-opportunity/",views.job_internship_opportunity,name="job_internship_opportunity"),
   path("job-internship-opportunity-api/",views.job_internship_opportunity_api,name="job_internship_opportunity_api"),
]