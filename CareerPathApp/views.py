import os
import json
import re

from google import genai

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login

from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import StudentProfile, CareerAssessment
# from django.contrib.auth.decorators import login_required

# Create your views here.
# home
def home(request):
    return render(request,'home.html')

# register
def register(request):
    if request.method == 'POST':

       name=request.POST.get("name")
       email=request.POST.get("email")
       phone =request.POST.get("phone")
       education=request.POST.get("education")
       password=request.POST.get("password")
       confirm_password=request.POST.get("confirm_password")

       #   password
       if password != confirm_password:
         return render(request,'register.html',{"error":"Password do not match."})

      # Email already exists check
       if User.objects.filter(username=email).exists():
         return render(request,'register.html',{"error":"An account with this email already exists."})

        # Create User
       user=User.objects.create_user(
         username=email,
         email=email,
         password=password
    )

        # create student profile
       StudentProfile.objects.create(
         user=user,
         name=name,
         email=email,
         phone=phone,
         education=education,
         skills=""
    )

      # login after registeration
       login(request,user)
       return redirect('home')

    return render(request,'register.html')

# student profile
def student_profile(request):

   if not request.user.is_authenticated:
      return redirect('register')

   profile=StudentProfile.objects.get(user=request.user)

   if request.method == 'POST':

      profile.name=request.POST.get('name','')
      profile.email=request.POST.get('email','')
      profile.phone=request.POST.get('phone','')
      profile.education=request.POST.get('education','')
      profile.skills=request.POST.get('skills','')

      profile.save()

      return redirect('career_assessment')
   return render(request,'student_profile.html',{'profile':profile})

# ==================== CAREER ASSESSMENT ====================

def career_assessment(request):

    if not request.user.is_authenticated:
        return redirect('register')

    if request.method == 'POST':

        interest = request.POST.get("interest")
        strength = request.POST.get("strength")
        work_style = request.POST.get("work_style")
        career_goal = request.POST.get("career_goal")

        CareerAssessment.objects.update_or_create(
            user=request.user,
            defaults={
                "interest": interest,
                "strength": strength,
                "work_style": work_style,
                "career_goal": career_goal,
            }
        )

        return redirect('career_match')

    return render(
        request,
        'career_assessment.html'
    )

# career match
def career_match(request):
   if not request.user.is_authenticated:
      return redirect('register')

   assessment=CareerAssessment.objects.get(user=request.user)

   career ='Software Developer'
   score=90

   if assessment.interest == 'Data':
      career ='Data Analyst'
      score=92

   elif assessment.interest=='Design':
      career = 'UI/UX Designer'
      score =89

   elif assessment.interest == "Business":
        career = "Business Analyst"
        score = 88

   elif assessment.interest == "Healthcare":
        career = "Healthcare Professional"
        score = 87

   elif assessment.interest == "Science":
        career = "Research Scientist"
        score = 86

   elif assessment.interest == "Law":
        career = "Legal Professional"
        score = 85

   return render(
        request,
        'career_match.html',
        {
            'career': career,
            'score': score,
            'assessment': assessment,
        }
    )
# explore career
def explore_careers(request):
    if not request.user.is_authenticated:
        return redirect('register')

    careers=[
         {
            "name": "Software Developer",
            "category": "Technology",
            "icon": "💻",
            "description": "Build websites, applications and software solutions."
        },
        {
            "name": "Data Analyst",
            "category": "Data & Analytics",
            "icon": "📊",
            "description": "Analyze data and generate useful business insights."
        },
        {
            "name": "AI / ML Engineer",
            "category": "Artificial Intelligence",
            "icon": "🤖",
            "description": "Build intelligent systems using AI and Machine Learning."
        },
        {
            "name": "UI/UX Designer",
            "category": "Design",
            "icon": "🎨",
            "description": "Design user-friendly digital products and experiences."
        },
        {
            "name": "Business Analyst",
            "category": "Business",
            "icon": "💼",
            "description": "Analyze business requirements and improve processes."
        },
        {
            "name": "Cyber Security Analyst",
            "category": "Technology",
            "icon": "🔐",
            "description": "Protect systems, networks and data from security threats."
        },
    ]
    return render(request,'explore_careers.html',{'career':careers})

# ================= CAREER DETAILS =================
def career_details(request, career_name):

    if not request.user.is_authenticated:
        return redirect('register')

    # Convert URL slug into readable career name
    career_name = career_name.replace("-", " ")
    career_name = career_name.replace("_", " ")
    career_name = " ".join(career_name.split()).title()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return render(request, "career_details.html", {
            "error": "Gemini API key is not configured."
        })

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
        Generate career information for: {career_name}

        Return ONLY valid JSON in this structure:
        {{
            "name": "Career name",
            "category": "Career category",
            "icon": "one suitable emoji",
            "description": "A clear career description in 2-3 sentences",
            "skills": [
                "Skill 1",
                "Skill 2",
                "Skill 3",
                "Skill 4",
                "Skill 5"
            ]
        }}

        Give realistic, useful information for students.
        Do not include markdown or text outside the JSON.
        """

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        response_text = response.text.strip()

        # Remove markdown fences if Gemini adds them
        if response_text.startswith("```"):
            response_text = response_text.replace("```json", "")
            response_text = response_text.replace("```", "")
            response_text = response_text.strip()

        details = json.loads(response_text)

        return render(
            request,
            "career_details.html",
            {
                "career": details
            }
        )

    except Exception as e:
        print("Gemini Career Details Error:", e)

        return render(request, "career_details.html", {
            "error": "Unable to generate career details right now. Please try again."
        })
# login
def user_login(request):
    if request.method == 'POST':

        email=request.POST.get('email')
        password=request.POST.get('password')

        user=authenticate(request,username=email,password=password)

        if user is not None:
            login(request,user)
            return redirect('home')
        else:
            return render(request,'login.html',{'error':'Invalid email or password.'})
    return render(request,'login.html')
# about
def about(request):
    return render(request,'about.html')

# work
def work(request):
    return render(request,'work.html')

# contact
def contact(request):
    return render(request,'contact.html')

# roadmap

def career_roadmap(request, career_name):
    if not request.user.is_authenticated:
        return redirect('register')

    career_name = career_name.replace("-", " ")
    career_name = career_name.replace("_", " ")
    career_name = " ".join(career_name.split()).title()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return render(request, "career_roadmap.html", {
            "career_name": career_name,
            "error": "Gemini API key is not configured."
        })

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
        Create a practical career learning roadmap for: {career_name}

        Return ONLY valid JSON with this exact structure:
        {{
            "intro": "Short introduction",
            "stages": [
                {{
                    "title": "Beginner",
                    "duration": "Estimated duration",
                    "skills": ["Skill 1", "Skill 2"],
                    "project": "One practical project",
                    "resources": ["Resource 1", "Resource 2"]
                }},
                {{
                    "title": "Intermediate",
                    "duration": "Estimated duration",
                    "skills": ["Skill 1", "Skill 2"],
                    "project": "One practical project",
                    "resources": ["Resource 1", "Resource 2"]
                }},
                {{
                    "title": "Advanced",
                    "duration": "Estimated duration",
                    "skills": ["Skill 1", "Skill 2"],
                    "project": "One practical project",
                    "resources": ["Resource 1", "Resource 2"]
                }},
                {{
                    "title": "Job Preparation",
                    "duration": "Estimated duration",
                    "skills": ["Skill 1", "Skill 2"],
                    "project": "Portfolio project",
                    "resources": ["Resource 1", "Resource 2"]
                }}
            ]
        }}

        Make the roadmap specific to this career.
        Give realistic durations and useful learning resources.
        Do not include markdown or text outside the JSON.
        """

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.replace("```json", "")
            response_text = response_text.replace("```", "").strip()

        roadmap = json.loads(response_text)

        return render(request, "career_roadmap.html", {
            "career_name": career_name,
            "roadmap": roadmap
        })

    except Exception as e:
        print("Gemini Career Roadmap Error:", e)

        return render(request, "career_roadmap.html", {
            "career_name": career_name,
            "error": "Unable to generate roadmap right now. Please try again."
        })
# features chatboat

# ================= AI CAREER CHATBOT =================
from django.urls import reverse
# ================= AI CAREER CHATBOT =================

def career_chatbot(request):
    return render(request, "career_chatbot.html")


@csrf_exempt
@require_POST
def chatbot_api(request):

    try:

        # ================= LOGIN / REGISTER CHECK =================

        if not request.user.is_authenticated:

            return JsonResponse({
                "error": "Please register or login to use the chatbot.",
                "redirect_url": reverse("register")
            }, status=401)


        # ================= GET REQUEST DATA =================

        data = json.loads(request.body)

        question = data.get("message", "").strip()

        history = data.get("history", [])


        # ================= QUESTION VALIDATION =================

        if not question:

            return JsonResponse(
                {
                    "error": "Please enter your question."
                },
                status=400
            )


        # ================= HISTORY VALIDATION =================

        if not isinstance(history, list):

            history = []


        # Keep only latest 10 messages

        history = history[-10:]


        # ================= GEMINI API KEY =================

        api_key = os.getenv("GEMINI_API_KEY")


        if not api_key:

            return JsonResponse(
                {
                    "error": "Gemini API key is not configured."
                },
                status=500
            )


        # ================= GEMINI CLIENT =================

        client = genai.Client(
            api_key=api_key
        )


        # ================= CONVERSATION HISTORY =================

        history_text = ""


        for item in history:

            if not isinstance(item, dict):

                continue


            role = item.get(
                "role",
                ""
            )


            content = item.get(
                "content",
                ""
            )


            if (
                role in ["user", "assistant"]
                and isinstance(content, str)
            ):

                history_text += (
                    f"{role}: {content}\n"
                )


        # ================= PROMPT =================

        prompt = f"""
You are CareerPath's AI Career Assistant.

Help students with:

- Career guidance
- Python and Django
- AI and Machine Learning
- Skills and courses
- Resume and interview preparation
- Jobs and internships

Give clear, practical and helpful answers.

Use the previous conversation to understand
follow-up questions.

If the question is unrelated to careers,
answer politely and guide the user back
to career-related topics.

Previous conversation:

{history_text}

Current user question:

{question}
"""


        # =====================================================
        # GEMINI REQUEST WITH RETRY
        # =====================================================

        response = None

        last_error = None


        for attempt in range(3):

            try:

                print(
                    f"Chatbot Gemini attempt {attempt + 1}"
                )


                response = client.models.generate_content(

                    model="gemini-3.5-flash-lite",

                    contents=prompt

                )


                # Check Gemini response

                if response and response.text:

                    print(
                        f"Chatbot Gemini attempt {attempt + 1} successful"
                    )

                    break


                else:

                    print(
                        f"Chatbot Gemini attempt {attempt + 1} returned empty response"
                    )


            except Exception as e:

                last_error = e

                response = None


                print(
                    f"Chatbot Gemini attempt {attempt + 1} failed:",
                    e
                )


        # =====================================================
        # FINAL RESPONSE CHECK
        # =====================================================

        if response is None or not response.text:

            print(
                "Chatbot Gemini final error:",
                last_error
            )


            return JsonResponse(
                {
                    "error":
                    "AI is temporarily unavailable. Please try again."
                },
                status=503
            )


        # ================= SUCCESS RESPONSE =================

        reply = response.text.strip()


        return JsonResponse({
            "reply": reply
        })


    # =========================================================
    # INVALID JSON
    # =========================================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error": "Invalid request data."
            },
            status=400
        )


    # =========================================================
    # OTHER ERRORS
    # =========================================================

    except Exception as e:

        print(
            "Career Chatbot Error:",
            e
        )


        return JsonResponse(
            {
                "error":
                "Unable to generate a response. Please try again."
            },
            status=500
        )

# AI MOCK INTERVIEW
def mock_interview(request):
    return render(
        request,
        "mock_interview.html"
    )


# NORMALIZE TEXT
def normalize_mock_text(text):


    return " ".join(
        str(text)
        .lower()
        .replace("?", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("!", " ")
        .replace(":", " ")
        .replace(";", " ")
        .strip()
        .split()
    )

# EXPLANATION REQUEST DETECTION
def is_explanation_request(message):

    text = normalize_mock_text(
        message
    )


    phrases = [

        "explain",

        "please explain",

        "explain this",

        "explain this question",

        "explain the question",

        "please explain this question",

        "can you explain this",

        "can you explain the question",

        "i dont understand",

        "i don't understand",

        "i do not understand",

        "dont understand",

        "i dont know",

        "i don't know",

        "i do not know",

        "dont know",

        "not sure",

        "i am not sure",

        "i'm not sure",

        "give me the answer",

        "tell me the answer",

        "what is the answer",

        "show me the answer"

    ]


    if text in phrases:
        return True


    keywords = [

        "explain this question",

        "explain the question",

        "please explain",

        "can you explain",

        "i dont understand this question",

        "i don't understand this question",

        "give me the answer",

        "tell me the answer"

    ]


    for keyword in keywords:

        if keyword in text:

            return True


    return False


# CREATE INTERVIEW MEMORY
def create_mock_interview_memory(
    subject,
    level,
    profile_context="",
    assessment_context=""
):

    return {

        "subject": subject,

        "level": level,

        "profile_context": profile_context,

        "assessment_context": assessment_context,

        "asked_questions": [],

        "covered_concepts": [],

        "explained_questions": [],

        "correct_answers": 0,

        "partial_answers": 0,

        "incorrect_answers": 0,

        "current_question": "",

        "current_concept": "",

        "interview_active": True

    }


# DUPLICATE QUESTION CHECK
def is_duplicate_mock_question(
    new_question,
    old_questions
):

    new_text = normalize_mock_text(
        new_question
    )


    for old_question in old_questions:

        old_text = normalize_mock_text(
            old_question
        )


        if new_text == old_text:

            return True


    return False

# GENERATE NEW QUESTION
def generate_new_mock_question(
    client,
    memory
):

    subject = memory.get(
        "subject",
        ""
    )


    level = memory.get(
        "level",
        "Fresher"
    )


    asked_questions = memory.get(
        "asked_questions",
        []
    )[-15:]


    covered_concepts = memory.get(
        "covered_concepts",
        []
    )[-15:]


    profile_context = memory.get(
        "profile_context",
        ""
    )


    assessment_context = memory.get(
        "assessment_context",
        ""
    )


    level_rules = {

        "Fresher": """
Basic concepts, fundamentals, simple practical questions,
basic coding and simple debugging.
Do not ask advanced, architecture or senior-level questions.
""",

        "Beginner": """
Fundamentals, concept understanding, simple practical
implementation, easy coding and debugging.
""",

        "Intermediate": """
Deeper concepts, practical implementation, problem solving,
debugging and moderate coding.
""",

        "Experienced": """
Advanced concepts, complex problem solving, advanced
debugging, architecture, performance and optimization.
"""
    }


    previous_questions = "\n".join(

        f"- {question}"

        for question in asked_questions

    )


    previous_concepts = "\n".join(

        f"- {concept}"

        for concept in covered_concepts

    )


    prompt = f"""

You are CareerPath's AI Technical Mock Interviewer.

Generate EXACTLY ONE technical interview question.


SUBJECT / TECHNOLOGY:
{subject}


INTERVIEW LEVEL:
{level}


LEVEL RULES:
{level_rules[level]}


STUDENT PROFILE:
{profile_context}


CAREER CONTEXT:
{assessment_context}


PREVIOUS QUESTIONS:
{previous_questions}


PREVIOUSLY COVERED CONCEPTS:
{previous_concepts}


IMPORTANT RULES:

1. The user's subject is the PRIMARY topic.

2. The subject can be any technical field.

3. Stay strictly relevant to the subject.

4. Follow the selected interview level strictly.

5. Generate exactly ONE question.

6. Never repeat a previous question.

7. Never generate a near-identical question.

8. NEVER use a concept already listed under
   PREVIOUSLY COVERED CONCEPTS.

9. Select a NEW concept.

10. Vary the question type.

11. Possible question types:
    - Definition
    - Conceptual
    - Difference
    - Why / How
    - Output-based
    - Coding
    - Debugging
    - Practical
    - Scenario

12. For Fresher, keep the question basic.

13. For Beginner, keep it foundational.

14. For Intermediate, use moderate problem solving.

15. For Experienced, use advanced professional questions.

16. Do not give the answer.

17. Do not give hints.

18. Do not give explanation.

19. Do not generate multiple questions.

20. Return ONLY JSON.


Return exactly:

{{
    "question": "One interview question",
    "concept": "New concept being tested",
    "type": "Question type",
    "difficulty": "{level}"
}}
"""


    response = client.models.generate_content(

        model="gemini-3.5-flash-lite",

        contents=prompt,

        config={
            "response_mime_type":
            "application/json"
        }

    )


    if not response or not response.text:

        raise Exception(
            "Gemini returned empty question."
        )


    result = json.loads(
        response.text.strip()
    )


    question = str(
        result.get(
            "question",
            ""
        )
    ).strip()


    concept = str(
        result.get(
            "concept",
            ""
        )
    ).strip()


    question_type = str(
        result.get(
            "type",
            ""
        )
    ).strip()


    difficulty = str(
        result.get(
            "difficulty",
            level
        )
    ).strip()


    if not question:

        raise Exception(
            "AI did not generate a question."
        )


    # Strong duplicate check
    if is_duplicate_mock_question(

        question,

        asked_questions

    ):

        raise Exception(
            "AI generated a repeated question."
        )


    # Avoid exact repeated concept
    normalized_concept = normalize_mock_text(
        concept
    )


    for old_concept in covered_concepts:

        if (
            normalized_concept
            ==
            normalize_mock_text(
                old_concept
            )
        ):

            raise Exception(
                "AI generated a repeated concept."
            )


    return {

        "question":
        question,

        "concept":
        concept,

        "type":
        question_type,

        "difficulty":
        difficulty

    }

# MOCK INTERVIEW API
@csrf_exempt
@require_POST
def mock_interview_api(request):

    try:

        # ====================================================
        # LOGIN CHECK
        # ====================================================

        if not request.user.is_authenticated:

            return JsonResponse(

                {
                    "error":
                    "Authentication required.",

                    "redirect_url":
                    reverse("register")
                },

                status=401

            )


        # ====================================================
        # REQUEST DATA
        # ====================================================

        try:

            data = json.loads(
                request.body
            )

        except json.JSONDecodeError:

            return JsonResponse(

                {
                    "error":
                    "Invalid request data."
                },

                status=400

            )


        subject = str(
            data.get(
                "subject",
                ""
            )
        ).strip()


        level = str(
            data.get(
                "level",
                ""
            )
        ).strip()


        action = str(
            data.get(
                "action",
                "start"
            )
        ).strip().lower()


        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()


        # ====================================================
        # VALIDATION
        # ====================================================

        if not subject:

            return JsonResponse(

                {
                    "error":
                    "Please enter your subject or technology."
                },

                status=400

            )


        allowed_levels = [

            "Fresher",

            "Beginner",

            "Intermediate",

            "Experienced"

        ]


        if level not in allowed_levels:

            return JsonResponse(

                {
                    "error":
                    "Please select a valid interview level."
                },

                status=400

            )


        # ====================================================
        # API KEY
        # ====================================================

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )


        if not api_key:

            return JsonResponse(

                {
                    "error":
                    "Gemini API key is not configured."
                },

                status=500

            )


        # ====================================================
        # GET PROFILE
        # ====================================================

        profile_context = ""


        try:

            profile = (
                StudentProfile.objects
                .filter(
                    user=request.user
                )
                .first()
            )


            if profile:

                profile_context = f"""
Education:
{getattr(profile, "education", "")}

Skills:
{getattr(profile, "skills", "")}
"""


        except Exception as e:

            print(
                "Mock Interview Profile Error:",
                e
            )


        # ====================================================
        # GET ASSESSMENT
        # ====================================================

        assessment_context = ""


        try:

            assessment = (
                CareerAssessment.objects
                .filter(
                    user=request.user
                )
                .first()
            )


            if assessment:

                assessment_context = f"""
Interest:
{getattr(assessment, "interest", "")}

Strength:
{getattr(assessment, "strength", "")}

Career Goal:
{getattr(assessment, "career_goal", "")}
"""


        except Exception as e:

            print(
                "Mock Interview Assessment Error:",
                e
            )


        # ====================================================
        # GEMINI CLIENT
        # ====================================================

        client = genai.Client(
            api_key=api_key
        )


        # ====================================================
        # SESSION MEMORY
        # ====================================================

        memory = request.session.get(

            "mock_interview_memory",

            {}

        )


        # ====================================================
        # START INTERVIEW
        # ====================================================

        if action == "start":

            memory = create_mock_interview_memory(

                subject=subject,

                level=level,

                profile_context=profile_context,

                assessment_context=assessment_context

            )


            # -----------------------------------------------
            # Generate first question
            # -----------------------------------------------

            try:

                result = generate_new_mock_question(

                    client,

                    memory

                )


            except Exception as e:

                print(
                    "Mock Interview Start Error:",
                    e
                )


                return JsonResponse(

                    {
                        "error":
                        "Unable to generate interview question right now. Please try again."
                    },

                    status=503

                )


            question = result["question"]

            concept = result["concept"]


            memory["asked_questions"] = [
                question
            ]


            memory["covered_concepts"] = (

                [concept]
                if concept
                else []

            )


            memory["current_question"] = (
                question
            )


            memory["current_concept"] = (
                concept
            )


            memory["interview_active"] = (
                True
            )


            request.session[
                "mock_interview_memory"
            ] = memory


            request.session.modified = True


            return JsonResponse(

                {

                    "success":
                    True,

                    "question":
                    question,

                    "concept":
                    concept,

                    "type":
                    result["type"],

                    "difficulty":
                    result["difficulty"]

                }

            )


        # ====================================================
        # CHECK ACTIVE INTERVIEW
        # ====================================================

        if not memory:

            return JsonResponse(

                {
                    "error":
                    "Please start the interview first."
                },

                status=400

            )


        if not memory.get(
            "interview_active",
            False
        ):

            return JsonResponse(

                {
                    "error":
                    "This interview has ended. Please start a new interview."
                },

                status=400

            )


        # ====================================================
        # NEXT QUESTION
        # ====================================================

        if action == "next":

            try:

                result = generate_new_mock_question(

                    client,

                    memory

                )


            except Exception as e:

                print(
                    "Mock Interview Next Error:",
                    e
                )


                return JsonResponse(

                    {
                        "error":
                        "Unable to generate a new question right now. Please try again."
                    },

                    status=503

                )


            question = result["question"]

            concept = result["concept"]


            memory["asked_questions"] = (

                memory.get(
                    "asked_questions",
                    []
                )

                +

                [question]

            )[-20:]


            if concept:

                memory["covered_concepts"] = (

                    memory.get(
                        "covered_concepts",
                        []
                    )

                    +

                    [concept]

                )[-20:]


            memory["current_question"] = (
                question
            )


            memory["current_concept"] = (
                concept
            )


            memory["interview_active"] = (
                True
            )


            request.session[
                "mock_interview_memory"
            ] = memory


            request.session.modified = True


            return JsonResponse(

                {

                    "success":
                    True,

                    "question":
                    question,

                    "concept":
                    concept,

                    "type":
                    result["type"],

                    "difficulty":
                    result["difficulty"]

                }

            )


        # ====================================================
        # END INTERVIEW
        # ====================================================

        if action == "end":

            memory["interview_active"] = (
                False
            )


            request.session[
                "mock_interview_memory"
            ] = memory


            request.session.modified = True


            return JsonResponse(

                {
                    "success":
                    True,

                    "message":
                    "Interview ended."
                }

            )


        # ====================================================
        # ANSWER
        # ====================================================

        if action == "answer":

            current_question = str(

                memory.get(
                    "current_question",
                    ""
                )

            ).strip()


            current_concept = str(

                memory.get(
                    "current_concept",
                    ""
                )

            ).strip()


            if not current_question:

                return JsonResponse(

                    {
                        "error":
                        "No active question found."
                    },

                    status=400

                )


            if not message:

                return JsonResponse(

                    {
                        "error":
                        "Please enter your answer."
                    },

                    status=400

                )


            # =================================================
            # EXPLANATION REQUEST
            # =================================================

            wants_explanation = (
                is_explanation_request(
                    message
                )
            )


            if wants_explanation:

                evaluation_prompt = f"""

You are CareerPath's AI Interview Tutor.

The candidate wants the CURRENT interview question
explained.

Subject:
{subject}

Interview Level:
{level}

Current Question:
{current_question}

Concept:
{current_concept}


IMPORTANT:

1. Do NOT evaluate the candidate's previous answer.

2. Give the COMPLETE correct answer.

3. Explain the concept simply.

4. Match the selected level.

5. Give a simple example.

6. Give one important interview point.

7. Do NOT generate another question.

8. Do NOT move to the next question.

Return ONLY valid JSON:

{{
    "correct_answer": "Complete correct answer",
    "explanation": "Simple explanation",
    "example": "Simple example",
    "interview_point": "Important interview point"
}}
"""


            else:

                # ==========================================
                # NORMAL ANSWER EVALUATION
                # ==========================================

                evaluation_prompt = f"""

You are CareerPath's AI Technical Interview Evaluator.

Evaluate the candidate's answer to the CURRENT question.

Subject:
{subject}

Interview Level:
{level}

Current Question:
{current_question}

Concept:
{current_concept}

Candidate Answer:
{message}


IMPORTANT:

1. Carefully check whether the candidate has
   answered ALL parts of the question.

2. Classify the answer as exactly:

   correct
   partial
   incorrect

3. If the question asks for multiple things,
   the answer is CORRECT only when all important
   parts are answered correctly.

4. If the answer is correct:
   confirm why it is correct.

5. If the answer is partial:
   clearly explain what was correct and
   what was missing.

6. If the answer is incorrect:
   clearly identify the mistake.

7. For partial or incorrect:
   ALWAYS provide the COMPLETE correct answer.

8. Give a simple example.

9. Give one important interview point.

10. Do NOT generate a new question.

11. Do NOT repeat the current question.

12. Do NOT move to the next question.

13. Keep the current question active.

Return ONLY valid JSON:

{{
    "result": "correct / partial / incorrect",
    "feedback": "Clear evaluation",
    "correct_answer": "Complete correct answer",
    "example": "Simple example",
    "interview_point": "Important interview point"
}}
"""


            # =================================================
            # ONE GEMINI CALL
            # =================================================

            try:

                response = client.models.generate_content(

                    model="gemini-3.5-flash-lite",

                    contents=evaluation_prompt,

                    config={
                        "response_mime_type":
                        "application/json"
                    }

                )


            except Exception as e:

                print(
                    "Mock Interview Answer Error:",
                    e
                )


                return JsonResponse(

                    {
                        "error":
                        "Unable to process your answer right now. Please try again."
                    },

                    status=503

                )


            if not response or not response.text:

                return JsonResponse(

                    {
                        "error":
                        "AI did not return a response."
                    },

                    status=503

                )


            # =================================================
            # PARSE AI RESPONSE
            # =================================================

            try:

                evaluation = json.loads(

                    response.text.strip()

                )


            except json.JSONDecodeError:

                print(
                    "Mock Interview JSON Error:",
                    response.text
                )


                return JsonResponse(

                    {
                        "error":
                        "AI returned invalid response data."
                    },

                    status=500

                )


            # =================================================
            # EXPLANATION RESPONSE
            # =================================================

            if wants_explanation:

                correct_answer = str(

                    evaluation.get(
                        "correct_answer",
                        ""
                    )

                ).strip()


                explanation = str(

                    evaluation.get(
                        "explanation",
                        ""
                    )

                ).strip()


                example = str(

                    evaluation.get(
                        "example",
                        ""
                    )

                ).strip()


                interview_point = str(

                    evaluation.get(
                        "interview_point",
                        ""
                    )

                ).strip()


                reply = ""


                if correct_answer:

                    reply += (
                        "Correct Answer:\n"
                        +
                        correct_answer
                    )


                if explanation:

                    reply += (
                        "\n\nExplanation:\n"
                        +
                        explanation
                    )


                if example:

                    reply += (
                        "\n\nExample:\n"
                        +
                        example
                    )


                if interview_point:

                    reply += (
                        "\n\nInterview Point:\n"
                        +
                        interview_point
                    )


                explained_questions = (

                    memory.get(
                        "explained_questions",
                        []
                    )

                )


                if current_question not in (

                    explained_questions

                ):

                    explained_questions.append(
                        current_question
                    )


                memory[
                    "explained_questions"
                ] = explained_questions[-20:]


                request.session[
                    "mock_interview_memory"
                ] = memory


                request.session.modified = True


                return JsonResponse(

                    {

                        "success":
                        True,

                        "result":
                        "explained",

                        "reply":
                        reply,

                        "ask_next":
                        True

                    }

                )


            # =================================================
            # NORMAL ANSWER RESPONSE
            # =================================================

            result_type = str(

                evaluation.get(
                    "result",
                    "partial"
                )

            ).strip().lower()


            feedback = str(

                evaluation.get(
                    "feedback",
                    ""
                )

            ).strip()


            correct_answer = str(

                evaluation.get(
                    "correct_answer",
                    ""
                )

            ).strip()


            example = str(

                evaluation.get(
                    "example",
                    ""
                )

            ).strip()


            interview_point = str(

                evaluation.get(
                    "interview_point",
                    ""
                )

            ).strip()


            # =================================================
            # BUILD RESPONSE
            # =================================================

            if result_type == "correct":

                reply = (

                    "Correct.\n\n"
                    +
                    feedback
                )


            elif result_type == "partial":

                reply = (

                    "Partially correct.\n\n"
                    +
                    feedback
                )


            else:

                reply = (

                    "Your answer needs correction.\n\n"
                    +
                    feedback
                )


            if correct_answer:

                reply += (

                    "\n\nCorrect Answer:\n"
                    +
                    correct_answer

                )


            if example:

                reply += (

                    "\n\nExample:\n"
                    +
                    example

                )


            if interview_point:

                reply += (

                    "\n\nInterview Point:\n"
                    +
                    interview_point

                )


            # =================================================
            # UPDATE SCORE
            # =================================================

            if result_type == "correct":

                memory["correct_answers"] = (

                    memory.get(
                        "correct_answers",
                        0
                    )

                    +

                    1

                )


            elif result_type == "partial":

                memory["partial_answers"] = (

                    memory.get(
                        "partial_answers",
                        0
                    )

                    +

                    1

                )


            else:

                memory["incorrect_answers"] = (

                    memory.get(
                        "incorrect_answers",
                        0
                    )

                    +

                    1

                )


            request.session[
                "mock_interview_memory"
            ] = memory


            request.session.modified = True


            # =================================================
            # ASK USER WHETHER TO CONTINUE
            # =================================================

            return JsonResponse(

                {

                    "success":
                    True,

                    "result":
                    result_type,

                    "reply":
                    reply,

                    "ask_next":
                    True

                }

            )


        # ====================================================
        # INVALID ACTION
        # ====================================================

        return JsonResponse(

            {
                "error":
                "Invalid interview action."
            },

            status=400

        )


    except Exception as e:

        print(
            "Mock Interview API Error:",
            e
        )


        return JsonResponse(

            {
                "error":
                "Unable to process mock interview. Please try again."
            },

            status=500

        )

# quiz
def career_aptitude_quiz(request):
    return render(request,'career_aptitude_quiz.html')

@csrf_exempt
@require_POST
def career_aptitude_api(request):

    try:

        # =========================================================
        # LOGIN CHECK
        # =========================================================

        if not request.user.is_authenticated:

            return JsonResponse(
                {
                    "error":
                        "Please register or login to use the aptitude quiz.",

                    "redirect_url":
                        reverse("register")
                },
                status=401
            )


        # =========================================================
        # READ REQUEST
        # =========================================================

        try:

            data = json.loads(
                request.body or "{}"
            )

        except json.JSONDecodeError:

            return JsonResponse(
                {
                    "error":
                        "Invalid request data."
                },
                status=400
            )


        # =========================================================
        # ACTION
        # =========================================================

        action = str(
            data.get(
                "action",
                "generate"
            )
        ).strip().lower()


        # =========================================================
        # SUBJECT / INTEREST
        # =========================================================

        user_interest = str(
            data.get("subject")
            or data.get("interest")
            or ""
        ).strip()


        if not user_interest:

            return JsonResponse(
                {
                    "error":
                        "Please enter your subject or field of interest."
                },
                status=400
            )


        # =========================================================
        # GEMINI API KEY
        # =========================================================

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )


        if not api_key:

            return JsonResponse(
                {
                    "error":
                        "Gemini API key is not configured."
                },
                status=500
            )


        client = genai.Client(
            api_key=api_key
        )


        # =========================================================
        # GENERATE QUIZ
        # =========================================================

        if action == "generate":

            prompt = f"""
You are CareerPath's AI Career Aptitude Quiz Generator.

The student selected this subject or field:

{user_interest}

Generate a personalized aptitude and knowledge assessment
specifically for this subject.

The questions MUST be directly related to the selected subject.

For example:

If the subject is Python:
- Python fundamentals
- Python programming
- coding logic
- debugging
- functions
- lists
- OOP
- Python applications
- Django where relevant

If the subject is Data Analytics:
- data interpretation
- SQL
- charts
- statistics
- patterns
- analytical thinking

If the subject is AI/ML:
- AI concepts
- machine learning
- models
- data
- logical thinking
- practical AI applications

For any other subject, generate questions specifically
related to that subject.

IMPORTANT:

This quiz HAS correct and incorrect answers.

Every question must have exactly ONE correct answer.

The correct answer must be objectively correct.

Do not create questions where multiple answers can be correct.

QUESTION RULES:

1. Generate exactly 10 questions.
2. Questions must be directly related to the selected subject.
3. Every question must have exactly 4 options.
4. Every question must have exactly one correct answer.
5. The correct_answer must exactly match one of the options.
6. Keep questions short and easy to understand.
7. Prefer 8 to 18 words per question.
8. Keep options short.
9. Avoid duplicate questions.
10. Cover different concepts from the selected subject.
11. Use simple English.
12. Avoid sensitive personal questions.
13. Do not include explanations outside JSON.
14. Do not include markdown.
15. Return ONLY valid JSON.

Use exactly this structure:

{{
    "questions": [
        {{
            "question":
                "Question text",

            "options": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4"
            ],

            "correct_answer":
                "Option 1"
        }}
    ]
}}
"""


            response = client.models.generate_content(

                model =
                    "gemini-3.5-flash-lite",

                contents =
                    prompt,

                config = {

                    "response_mime_type":
                        "application/json"

                }

            )


            if (
                not response
                or
                not response.text
            ):

                return JsonResponse(
                    {
                        "error":
                            "AI did not return quiz questions."
                    },
                    status=500
                )


            response_text =response.text.strip()


            # =====================================================
            # REMOVE MARKDOWN FENCES
            # =====================================================

            if response_text.startswith("```"):

                response_text = (
                    response_text
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )


            # =====================================================
            # PARSE JSON
            # =====================================================

            try:

                quiz_data =json.loads(
                        response_text
                    )

            except json.JSONDecodeError:

                print(
                    "Career Aptitude Generate JSON Error:",
                    response_text
                )

                return JsonResponse(
                    {
                        "error":
                            "AI returned invalid quiz data."
                    },
                    status=500
                )


            # =====================================================
            # QUESTIONS
            # =====================================================

            raw_questions =quiz_data.get(
                    "questions",
                    []
                )


            if not isinstance(
                raw_questions,
                list
            ):

                return JsonResponse(
                    {
                        "error":
                            "Invalid question data received."
                    },
                    status=500
                )


            valid_questions = []


            # =====================================================
            # VALIDATE EACH QUESTION
            # =====================================================

            for item in raw_questions:

                if not isinstance(
                    item,
                    dict
                ):

                    continue


                question = str(
                    item.get(
                        "question",
                        ""
                    )
                ).strip()


                raw_options =item.get(
                        "options",
                        []
                    )


                correct_answer =str(
                        item.get(
                            "correct_answer",
                            ""
                        )
                    ).strip()


                if not question:

                    continue


                if not isinstance(
                    raw_options,
                    list
                ):

                    continue


                cleaned_options = []


                for option in raw_options:

                    if isinstance(
                        option,
                        dict
                    ):

                        option =option.get(
                                "text",
                                ""
                            )


                    option_text =str(
                            option
                        ).strip()


                    if option_text:

                        cleaned_options.append(
                            option_text
                        )


                # EXACTLY 4 OPTIONS

                if len(
                    cleaned_options
                ) != 4:

                    continue


                # CORRECT ANSWER REQUIRED

                if not correct_answer:

                    continue


                # MUST MATCH ONE OPTION EXACTLY

                if correct_answer not in cleaned_options:

                    continue


                valid_questions.append(
                    {
                        "question":
                            question,

                        "options":
                            cleaned_options,

                        "correct_answer":
                            correct_answer
                    }
                )


            # =====================================================
            # MINIMUM QUESTIONS
            # =====================================================

            if len(
                valid_questions
            ) < 10:

                return JsonResponse(
                    {
                        "error":
                            "AI did not generate enough valid questions."
                    },
                    status=500
                )


            # EXACTLY 10 QUESTIONS

            valid_questions =valid_questions[:10]


            # =====================================================
            # RETURN QUIZ
            # =====================================================

            return JsonResponse(
                {
                    "success":
                        True,

                    "subject":
                        user_interest,

                    "interest":
                        user_interest,

                    "questions":
                        valid_questions
                }
            )


        # =========================================================
        # ANALYZE QUIZ
        # =========================================================

        if action == "analyze":

            questions =data.get(
                    "questions",
                    []
                )


            answers =data.get(
                    "answers",
                    []
                )


            if not isinstance(
                questions,
                list
            ):

                return JsonResponse(
                    {
                        "error":
                            "Invalid questions received."
                    },
                    status=400
                )


            if not isinstance(
                answers,
                list
            ):

                return JsonResponse(
                    {
                        "error":
                            "Invalid answers received."
                    },
                    status=400
                )


            if not questions:

                return JsonResponse(
                    {
                        "error":
                            "No questions available."
                    },
                    status=400
                )


            if len(questions) != len(answers):

                return JsonResponse(
                    {
                        "error":
                            "Question and answer data do not match."
                    },
                    status=400
                )


            # =====================================================
            # CALCULATE SCORE ON SERVER
            # =====================================================

            correct_count = 0

            wrong_count = 0

            question_results = []


            for index, question in enumerate(
                questions
            ):

                if not isinstance(
                    question,
                    dict
                ):

                    continue


                question_text =str(
                        question.get(
                            "question",
                            ""
                        )
                    ).strip()


                correct_answer =str(
                        question.get(
                            "correct_answer",
                            ""
                        )
                    ).strip()


                user_answer =str(
                        answers[index]
                        or
                        ""
                    ).strip()


                is_correct = (

                    bool(
                        correct_answer
                    )
                    and
                    user_answer.lower()
                    ==
                    correct_answer.lower()

                )


                if is_correct:

                    correct_count += 1

                    result_status ="correct"

                else:

                    wrong_count += 1

                    result_status ="wrong"


                question_results.append(
                    {
                        "question_number":
                            index + 1,

                        "question":
                            question_text,

                        "user_answer":
                            user_answer,

                        "correct_answer":
                            correct_answer,

                        "status":
                            result_status
                    }
                )


            # =====================================================
            # TOTAL
            # =====================================================

            total_questions =len(questions)


            # =====================================================
            # PERCENTAGE
            # =====================================================

            percentage = (

                round(
                    (
                        correct_count /
                        total_questions
                    ) * 100
                )

                if total_questions > 0

                else 0

            )


            # =====================================================
            # PERFORMANCE
            # =====================================================

            if percentage >= 80:

                performance ="Excellent Performance!"


            elif percentage >= 60:

                performance ="Good Performance!"


            elif percentage >= 40:

                performance ="Average Performance!"


            else:

                performance ="Needs Improvement!"


            # =====================================================
            # BUILD Q&A TEXT FOR AI
            # =====================================================

            qa_text = ""


            for item in question_results:

                qa_text += f"""
Question {item["question_number"]}:
{item["question"]}

Student Answer:
{item["user_answer"]}

Correct Answer:
{item["correct_answer"]}

Result:
{item["status"]}

--------------------------------
"""


            # =====================================================
            # AI CAREER ANALYSIS
            # =====================================================

            analysis_prompt = f"""
You are CareerPath's AI Career Aptitude Analyst.

Student selected subject:

{user_interest}

The student completed a 10-question aptitude assessment.

The numerical result is already calculated by the system:

Total Questions:
{total_questions}

Correct Answers:
{correct_count}

Wrong Answers:
{wrong_count}

Percentage:
{percentage}%

Performance:
{performance}

Do NOT change these numbers.

Analyze the student's answers to identify:

- strengths
- interests
- problem-solving approach
- learning style
- technical interests
- suitable career areas

Career recommendations must be related to:

1. The selected subject
2. The student's answers
3. The observed response pattern

Do not invent unsupported skills.

Keep the analysis simple and student-friendly.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_result":
        "Short 2 sentence conclusion.",

    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],

    "interests": [
        "Interest 1",
        "Interest 2",
        "Interest 3"
    ],

    "career_areas": [
        "Career Area 1",
        "Career Area 2",
        "Career Area 3"
    ],

    "analysis":
        "Clear 3 to 5 sentence analysis."
}}

Student Questions and Answers:

{qa_text}
"""


            analysis_response =client.models.generate_content(

                    model =
                        "gemini-3.5-flash-lite",

                    contents =
                        analysis_prompt,

                    config = {

                        "response_mime_type":
                            "application/json"

                    }

                )


            if (
                not analysis_response
                or
                not analysis_response.text
            ):

                return JsonResponse(
                    {
                        "success":
                            True,

                        "subject":
                            user_interest,

                        "interest":
                            user_interest,

                        "overall_score":
                            correct_count,

                        "percentage":
                            percentage,

                        "total_questions":
                            total_questions,

                        "correct_answers":
                            correct_count,

                        "wrong_answers":
                            wrong_count,

                        "performance":
                            performance,

                        "question_results":
                            question_results,

                        "overall_result":
                            "",

                        "strengths":
                            [],

                        "interests":
                            [],

                        "career_areas":
                            [],

                        "analysis":
                            ""
                    }
                )


            analysis_text =analysis_response.text.strip()


            # =====================================================
            # REMOVE MARKDOWN
            # =====================================================

            if analysis_text.startswith("```"):

                analysis_text = (
                    analysis_text
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )


            # =====================================================
            # PARSE AI ANALYSIS
            # =====================================================

            try:

                result_data =json.loads(
                        analysis_text
                    )

            except json.JSONDecodeError:

                print(
                    "Career Aptitude Analysis JSON Error:",
                    analysis_text
                )

                result_data = {}


            # =====================================================
            # GET AI FIELDS
            # =====================================================

            overall_result =str(
                    result_data.get(
                        "overall_result",
                        ""
                    )
                ).strip()


            strengths =result_data.get(
                    "strengths",
                    []
                )


            interests =result_data.get(
                    "interests",
                    []
                )


            career_areas =result_data.get(
                    "career_areas",
                    []
                )


            analysis =str(
                    result_data.get(
                        "analysis",
                        ""
                    )
                ).strip()


            if not isinstance(
                strengths,
                list
            ):

                strengths = []


            if not isinstance(
                interests,
                list
            ):

                interests = []


            if not isinstance(
                career_areas,
                list
            ):

                career_areas = []


            # =====================================================
            # FINAL RESPONSE
            # =====================================================

            return JsonResponse(
                {
                    "success":
                        True,

                    "subject":
                        user_interest,

                    "interest":
                        user_interest,

                    "overall_score":
                        correct_count,

                    "percentage":
                        percentage,

                    "total_questions":
                        total_questions,

                    "correct_answers":
                        correct_count,

                    "wrong_answers":
                        wrong_count,

                    "performance":
                        performance,

                    "question_results":
                        question_results,

                    "overall_result":
                        overall_result,

                    "strengths":
                        [
                            str(item).strip()
                            for item in strengths[:5]
                            if str(item).strip()
                        ],

                    "interests":
                        [
                            str(item).strip()
                            for item in interests[:5]
                            if str(item).strip()
                        ],

                    "career_areas":
                        [
                            str(item).strip()
                            for item in career_areas[:5]
                            if str(item).strip()
                        ],

                    "analysis":
                        analysis
                }
            )


        # =========================================================
        # INVALID ACTION
        # =========================================================

        return JsonResponse(
            {
                "error":
                    "Invalid aptitude quiz action."
            },
            status=400
        )


    except Exception as e:

        print(
            "Career Aptitude API Error:",
            repr(e)
        )


        return JsonResponse(
            {
                "error":
                    "Unable to process the aptitude quiz. Please try again."
            },
            status=500
        )

# ============================================================
# JOB & INTERNSHIP RECOMMENDATION PAGE
# ============================================================

def job_internship_recommendation(request):

    if not request.user.is_authenticated:
        return redirect("login")

    return render(
        request,
        "job_internship_recommendation.html"
    )
# ============================================================
# JOB & INTERNSHIP PROFILE ANALYSIS PAGE
# ============================================================

def job_internship_analysis(request):

    if not request.user.is_authenticated:
        return redirect("login")

    return render(
        request,
        "job_internship_analysis.html"
    )
@csrf_exempt
@require_POST
def job_internship_analysis_api(request):

    # ============================================================
    # LOGIN CHECK
    # ============================================================

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "message": "Login required."
            },
            status=401
        )

    try:

        # ========================================================
        # READ REQUEST DATA
        # ========================================================

        data = json.loads(request.body)

        # ========================================================
        # INTEREST
        # ========================================================

        interest = str(
            data.get(
                "interest",
                ""
            )
        ).strip()

        # ========================================================
        # SKILLS
        # ========================================================

        entered_skills = str(
            data.get(
                "skills",
                ""
            )
        ).strip()

        # ========================================================
        # EDUCATION
        # ========================================================

        education = str(
            data.get(
                "education",
                ""
            )
        ).strip()

        # ========================================================
        # VALIDATION
        # ========================================================

        if not interest:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Please enter your interest."
                },
                status=400
            )

        if not entered_skills:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Please enter your skills."
                },
                status=400
            )

        if not education:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Please enter your education."
                },
                status=400
            )

        # ========================================================
        # CLEAN SKILLS
        # ========================================================

        raw_skills = re.split(
            r"[,;\n]+",
            entered_skills
        )

        skills_list = []

        for skill in raw_skills:

            skill = skill.strip()

            if skill and skill not in skills_list:
                skills_list.append(skill)

        if not skills_list:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Please enter at least one valid skill."
                },
                status=400
            )

        # ========================================================
        # GEMINI PROMPT
        # ========================================================

        prompt = f"""
You are an AI career analysis assistant for CareerPath.

Analyze the student's career profile using ONLY these
three inputs:

1. Education
2. Selected Interest
3. Entered Skills

The student's name is NOT required and must NOT be used.

============================================================
STUDENT INPUT
============================================================

Education:
{education}

Selected Interest:
{interest}

Entered Skills:
{", ".join(skills_list)}

============================================================
ANALYSIS REQUIREMENTS
============================================================

Analyze the student's profile dynamically.

The analysis must be based specifically on the
education, interest and skills provided above.

Do NOT use a fixed career list.

Do NOT use a fixed skill-gap list.

Do NOT assume that every student belongs to the same field.

Do NOT always recommend the same careers.

The output must change when:

- Education changes
- Interest changes
- Skills change

============================================================
1. PROFILE SUMMARY
============================================================

Create a concise and factual summary of the student's
profile using:

- Education
- Selected Interest
- Entered Skills

Do not mention the student's name.

============================================================
2. INTEREST ALIGNMENT
============================================================

Explain how the student's education and entered skills
align with the selected interest.

The explanation must be specific to the actual input.

============================================================
3. MATCHING SKILLS
============================================================

Return ONLY the skills from the student's entered skills
that are relevant to the selected interest.

Do NOT invent skills.

Do NOT add skills that were not entered.

If all entered skills are relevant, return all relevant
entered skills.

============================================================
4. SKILL GAPS
============================================================

Identify useful skills that are missing from the student's
entered skills and would help with the selected interest
and suitable career direction.

Generate these dynamically.

Do NOT use a fixed list.

Do NOT include skills that are already present in the
entered skills.

============================================================
5. CAREER FOCUS
============================================================

Generate between 3 and 6 suitable career roles.

Career roles must be based on the combination of:

- Education
- Selected Interest
- Entered Skills

The roles should be practical and realistic for a
student/fresher.

Do NOT simply return the selected interest as a career.

Do NOT always return the same career roles.

For example, Python + Django + REST API + SQL may lead
to roles such as Python Developer, Backend Developer,
Django Developer, API Developer or Software Engineer.

These are examples only.

For other interests and skills, generate different
appropriate career roles.

============================================================
IMPORTANT
============================================================

- Education is required.
- Interest is required.
- Skills are required.
- Do not use student's name.
- Do not invent education.
- Do not invent entered skills.
- Matching skills must come from entered skills.
- Skill gaps must not duplicate entered skills.
- Career roles must be relevant to the actual profile.
- Return 3 to 6 career roles.
- Do not repeat career roles.
- Keep the recommendations practical for a fresher.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use ```json.

Do not add any explanation outside JSON.

Use exactly this structure:

{{
    "profile_summary": "Concise profile summary",
    "interest_alignment": "Specific explanation of interest alignment",
    "matching_skills": [
        "Skill 1",
        "Skill 2"
    ],
    "skill_gaps": [
        "Missing Skill 1",
        "Missing Skill 2"
    ],
    "career_focus": [
        "Career Role 1",
        "Career Role 2",
        "Career Role 3"
    ]
}}
"""

        # ========================================================
        # GEMINI API CALL
        # ========================================================

        try:

            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise Exception(
                    "Gemini API key is not configured."
                )

            client = genai.Client(
                api_key=api_key
            )
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config={
                   "response_mime_type": "application/json"
                }
            )
            ai_text=""

            if response and hasattr(
                response,
                "text"
            ):
                ai_text = response.text.strip()

                print("====================================")
                print("GEMINI RAW RESPONSE:")
                print(ai_text)
                print("====================================")
        except Exception as ai_error:

           ai_text = ""

           print(
             "Gemini Analysis Error:",
             ai_error
           )
        # ========================================================
        # INITIAL VALUES
        # ========================================================

        profile_summary = ""
        interest_alignment = ""
        matching_skills = []
        skill_gaps = []
        career_focus = []

        # ========================================================
        # PARSE AI RESPONSE
        # ========================================================

        if ai_text:

            try:

                cleaned_ai_text = ai_text.strip()

                # Remove markdown JSON block if Gemini adds it
                if cleaned_ai_text.startswith(
                    "```json"
                ):

                    cleaned_ai_text = (
                        cleaned_ai_text[7:]
                    )

                elif cleaned_ai_text.startswith(
                    "```"
                ):

                    cleaned_ai_text = (
                        cleaned_ai_text[3:]
                    )

                if cleaned_ai_text.endswith(
                    "```"
                ):

                    cleaned_ai_text = (
                        cleaned_ai_text[:-3]
                    )

                cleaned_ai_text = (
                    cleaned_ai_text.strip()
                )

                # Convert AI JSON string to Python dictionary
                ai_result = json.loads(
                    cleaned_ai_text
                )

                # =================================================
                # PROFILE SUMMARY
                # =================================================

                profile_summary = str(
                    ai_result.get(
                        "profile_summary",
                        ""
                    )
                ).strip()

                # =================================================
                # INTEREST ALIGNMENT
                # =================================================

                interest_alignment = str(
                    ai_result.get(
                        "interest_alignment",
                        ""
                    )
                ).strip()

                # =================================================
                # MATCHING SKILLS
                # =================================================

                matching_skills = ai_result.get(
                    "matching_skills",
                    []
                )

                # =================================================
                # SKILL GAPS
                # =================================================

                skill_gaps = ai_result.get(
                    "skill_gaps",
                    []
                )

                # =================================================
                # CAREER FOCUS
                # =================================================

                career_focus = ai_result.get(
                    "career_focus",
                    []
                )

                # =================================================
                # TYPE VALIDATION
                # =================================================

                if not isinstance(
                    matching_skills,
                    list
                ):
                    matching_skills = []

                if not isinstance(
                    skill_gaps,
                    list
                ):
                    skill_gaps = []

                if not isinstance(
                    career_focus,
                    list
                ):
                    career_focus = []

            except Exception as parse_error:

                print(
                    "AI JSON Parsing Error:",
                    parse_error
                )

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return JsonResponse(
            {
                "success": True,

                "education":
                    education,

                "interest":
                    interest,

                "skills":
                    skills_list,

                "profile_summary":
                    profile_summary,

                "interest_alignment":
                    interest_alignment,

                "matching_skills":
                    matching_skills,

                "skill_gaps":
                    skill_gaps,

                "career_focus":
                    career_focus,

                "ai_analysis":
                    ai_text
            }
        )

    # ============================================================
    # INVALID JSON
    # ============================================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid JSON request."
            },
            status=400
        )

    # ============================================================
    # OTHER ERRORS
    # ============================================================

    except Exception as e:

        print(
            "Job Internship Analysis API Error:",
            e
        )

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )