
import os
import json
import re

from google import genai

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme

from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import StudentProfile, CareerAssessment

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

        # ---------------- INTEREST ----------------

        interest = request.POST.get("interest")

        if interest == "Other":
            interest = request.POST.get("other_interest", "").strip()


        # ---------------- STRENGTH ----------------

        strength = request.POST.get("strength")

        if strength == "Other":
            strength = request.POST.get("other_strength", "").strip()


        # ---------------- WORK STYLE ----------------

        work_style = request.POST.get("work_style")

        if work_style == "Other":
            work_style = request.POST.get("other_work_style", "").strip()


        # ---------------- CAREER GOAL ----------------

        career_goal = request.POST.get("career_goal")

        if career_goal == "Other":
            career_goal = request.POST.get("other_career_goal", "").strip()


        # ---------------- SAVE ASSESSMENT ----------------

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

    try:
        assessment = CareerAssessment.objects.get(user=request.user)
    except CareerAssessment.DoesNotExist:
        return redirect('career_assessment')

    # User assessment data
    interest = assessment.interest
    strength = assessment.strength
    work_style = assessment.work_style
    career_goal = assessment.career_goal

    # Gemini API
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return render(
            request,
            'career_match.html',
            {
                'career': 'Career Match Unavailable',
                'score': 0,
                'assessment': assessment,
            }
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an expert career guidance system.

Analyze the student's profile and recommend the SINGLE BEST career
that genuinely matches the student's field.

IMPORTANT RULES:

1. The student's INTEREST is the primary field.
2. The career MUST belong to or be strongly related to the student's
   interest/field.
3. NEVER assume the field is Technology.
4. NEVER automatically recommend Software Developer, Data Analyst,
   AI Engineer, IT jobs, or other technology careers unless the
   student's actual interest supports them.
5. The interest can be ANY field, for example:
   Cricket, Sports, Biology, Teaching, Finance, Marketing,
   Fashion, Agriculture, Law, Music, Psychology, Design,
   Healthcare, Business, Science, Technology, etc.
6. If the interest is a custom field, generate a career specifically
   related to that custom field.
7. Use Strength, Work Style and Career Goal to refine the recommendation.
8. Do not change the student's field just because a more common career
   exists.
9. The recommended career must be realistic for the student's education
   and profile.
10. Match score must be between 70 and 98.
11. Return ONLY valid JSON.

Student Profile:

Interest: {interest}
Strongest Skill: {strength}
Work Style: {work_style}
Career Goal: {career_goal}

Return exactly:

{{

    "career": "single best career name",

    "interest_alignment": "very_strong",

    "strength_alignment": "strong",

    "work_style_alignment": "moderate",

    "career_goal_alignment": "strong"

}}

For each alignment field, use ONLY one of:
"very_strong", "strong", "moderate", "weak"
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        result = json.loads(response.text)

        career = result.get(
            "career",
           f"{interest} Professional"
        )

        score_map = {
            "very_strong": {
                "interest": 40,
                "strength": 25,
                "work": 20,
                "goal": 15
            },
            "strong": {
                "interest": 35,
                "strength": 20,
                "work": 15,
                "goal": 12
            },
            "moderate": {
                "interest": 25,
                "strength": 15,
                "work": 10,
                "goal": 8
            },
            "weak": {
                "interest": 15,
                "strength": 10,
                "work": 5,
                "goal": 5
            }
        }
        interest_level = result.get(
            "interest_alignment", "moderate"
        ).lower()

        strength_level = result.get(
            "strength_alignment", "moderate"
        ).lower()

        work_level = result.get(
            "work_style_alignment", "moderate"
        ).lower()

        goal_level = result.get(
            "career_goal_alignment", "moderate"
        ).lower()

        score = (
            score_map.get(interest_level, score_map["moderate"])["interest"]
            + score_map.get(strength_level, score_map["moderate"])["strength"]
            + score_map.get(work_level, score_map["moderate"])["work"]
            + score_map.get(goal_level, score_map["moderate"])["goal"]
        )

        score = max(40, min(score, 100))
    except Exception as e:

        print("Career Match Error:", e)

        # Dynamic fallback
        career = f"{interest} Professional"
        score = 80

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
    ],
    "career_path": [
        {{
            "title": "Career-specific first stage",
            "description": "What the student should do at this stage."
        }},
        {{
            "title": "Career-specific second stage",
            "description": "What the student should do at this stage."
        }},
        {{
            "title": "Career-specific third stage",
            "description": "What the student should do at this stage."
        }},
        {{
            "title": "Career-specific fourth stage",
            "description": "What the student should do at this stage."
        }},
        {{
            "title": "Career-specific fifth stage",
            "description": "What the student should do at this stage."
        }}
    ]
}}

The career_path must be specifically designed for the given career.

Do NOT use generic stages such as:
"Learn Skills", "Build Projects", "Get Experience", "Start Career".

For example, a teacher, fashion designer, cricketer, scientist,
doctor, lawyer, marketer and software engineer must have different
career paths.

Make every stage practical and relevant to the specific career.

Do not include markdown or text outside the JSON.

        Give realistic, useful information for students.
        Do not include markdown or text outside the JSON.
        """

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
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
            model="gemini-3.5-flash-lite",
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

# @login_required(login_url='login')
# def career_chatbot(request):
#     return render(request, 'CareerPathApp/career_chatbot.html')

@csrf_exempt
@require_POST
def chatbot_api(request):

    try:
        # ================= LOGIN CHECK =================

        if not request.user.is_authenticated:
            return JsonResponse({
                "error": "Please register or login to use the chatbot.",
                "redirect_url": reverse("register")
            }, status=401)

        # ================= REQUEST DATA =================

        data = json.loads(request.body)

        question = data.get("message", "").strip()
        history = data.get("history", [])

        if not question:
            return JsonResponse({
                "error": "Please enter your question."
            }, status=400)

        if not isinstance(history, list):
            history = []

        # Keep only the latest 10 messages
        history = history[-10:]

        # ================= GEMINI API KEY =================

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return JsonResponse({
                "error": "Gemini API key is not configured."
            }, status=500)

        # ================= GEMINI CLIENT =================

        client = genai.Client(api_key=api_key)

        # ================= CONVERSATION HISTORY =================

        history_text = ""

        for item in history:

            if not isinstance(item, dict):
                continue

            role = item.get("role", "")
            content = item.get("content", "")

            if (
                role in ["user", "assistant"]
                and isinstance(content, str)
            ):
                history_text += f"{role}: {content}\n"

        # ================= CAREER GUIDANCE PROMPT =================

        prompt = f"""
You are CareerPath's AI Career Guidance Assistant.

YOUR MAIN PURPOSE:
Help students explore, choose, prepare for, and build careers
in ANY field. You are not limited to technology or IT careers.

SUPPORTED CAREER FIELDS INCLUDE, BUT ARE NOT LIMITED TO:

- Government jobs and competitive exams such as UPSC, MPPSC,
  SSC, Banking and Railways
- Teaching, education and academic careers
- Science, Biology, Biotechnology and Research
- Healthcare and medical careers
- Commerce, Accounting, Finance and Economics
- Business, Management, Marketing and Entrepreneurship
- Law and legal careers
- Agriculture and environmental careers
- Sports, Cricket and physical education
- Fashion, Interior Design, Graphic Design and Arts
- Psychology, Social Work and Humanities
- Technology, Python, Django, AI, Machine Learning and Software
  Development
- Any other career or emerging field

YOUR RESPONSIBILITIES:

1. Explain careers, job roles and career options clearly.
2. Explain educational qualifications, eligibility and entrance exams.
3. Suggest relevant subjects, skills, courses and certifications.
4. Provide practical, step-by-step preparation plans and roadmaps.
5. Help students with college choices, competitive exams, portfolios,
   internships, job searches and interview preparation.
6. Help students compare careers fairly when they explicitly ask.
7. Personalize advice using education, interests and goals when known.
8. Focus on the specific field mentioned in the student's question.
9. Never assume every student wants an IT or technology career.
10. Never compare a career with technology unless the student asks.
11. Do not invent current exam dates, vacancies, eligibility rules,
    fees or official requirements.
12. For government exams, explain the relevant exam, syllabus,
    eligibility, preparation strategy and official verification sources.
13. If the student has not provided enough information, give useful
    general guidance first and ask a relevant follow-up question.

RESPONSE STYLE:

- Use simple, student-friendly language.
- Give clear, practical and relevant answers.
- Use headings, numbered steps and bullet points when useful.
- Answer the current question directly.
- Use previous conversation when it is relevant to the current question.
- Do not repeatedly advertise or redirect toward IT careers.
- If a question is unrelated to careers, answer briefly and politely
  guide the student back toward learning or career guidance.

IMPORTANT EXAMPLES:

- If asked about UPSC, explain UPSC and its preparation. Do not compare
  it with technology careers unless explicitly asked.
- If asked how to become a teacher, explain teaching qualifications,
  relevant exams and preparation.
- If asked about Biology careers, focus on Biology-related options.
- If asked about Fashion Design, explain fashion-related skills,
  courses and portfolio preparation.
- If asked about AI/ML, provide relevant AI/ML career guidance.

Use the conversation history to understand follow-up questions.
Do not treat a new topic as a follow-up unless context supports it.

Previous conversation:
{history_text}

Current user question:
{question}

Now answer the current question directly.
"""

        # ================= GEMINI REQUEST WITH RETRY =================

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

                if response and response.text:
                    print(
                        f"Chatbot Gemini attempt {attempt + 1} successful"
                    )
                    break

                print(
                    f"Chatbot Gemini attempt {attempt + 1} "
                    "returned empty response"
                )

            except Exception as e:
                last_error = e
                response = None

                print(
                    f"Chatbot Gemini attempt {attempt + 1} failed:",
                    e
                )

        # ================= FINAL RESPONSE CHECK =================

        if response is None or not response.text:

            print("Chatbot Gemini final error:", last_error)

            return JsonResponse({
                "error": "AI is temporarily unavailable. Please try again."
            }, status=503)

        # ================= SUCCESS RESPONSE =================

        reply = response.text.strip()

        return JsonResponse({
            "reply": reply
        })

    # ================= INVALID JSON =================

    except json.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid request data."
        }, status=400)

    # ================= OTHER ERRORS =================

    except Exception as e:
        print("Career Chatbot Error:", e)

        return JsonResponse({
            "error": "Unable to generate a response. Please try again."
        }, status=500)


# AI MOCK INTERVIEW
def mock_interview(request):
    return render(
        request,
        "mock_interview.html"
    )

# @login_required(login_url='login')
# def mock_interview(request):
#     return render(request, 'CareerPathApp/mock_interview.html')

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
          Ask simple, fundamental interview questions suitable
          for a fresher with little or no professional experience.

    Focus on:
    - Basic concepts of the selected subject
    - Definitions and fundamental terminology
    - Simple differences between concepts
    - Basic understanding and applications
    - Easy practical questions
    - Very simple examples or coding questions,
      only when relevant to the selected subject

    Questions must be short, clear and beginner-friendly.
    Do not ask advanced, senior-level or complex questions.
    Do not assume the candidate belongs to the IT field.
    """,

       "Beginner": """
    Ask foundational questions to check understanding
    of the selected subject.

    Include simple practical applications,
    basic problem-solving and easy examples.
    Avoid advanced or highly complex questions.
    """,

       "Intermediate": """
    Ask moderately challenging questions related to
    the selected subject.

    Include practical applications, problem-solving,
    conceptual understanding and relevant debugging
    or case-based questions where appropriate.
    """,

       "Experienced": """
    Ask advanced professional questions relevant to
    the selected subject and experience level.
 
    Include complex problem-solving, real-world scenarios,
    decision-making and advanced concepts where relevant.
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

1. The selected subject or field is the single source
   of truth for generating interview questions.

2. Support any technical or non-technical subject,
   including programming, science, education, business,
   design, healthcare and other professional fields.

3. Stay strictly relevant to the selected subject.

4. Follow the selected interview level and LEVEL RULES.

5. Generate exactly ONE interview question.

6. Never repeat a previous question.

7. Never generate an identical or near-identical question.

8. Never reuse a concept listed under
   PREVIOUSLY COVERED CONCEPTS.

9. Select a new, relevant concept for each question.

10. Vary the question type when appropriate:
    Definition, Conceptual, Difference, Why/How,
    Output-based, Coding, Debugging, Practical or Scenario.

11. Use only question types appropriate to the
    selected subject.

12. For Fresher, ask simple fundamental questions.

13. For Beginner, ask foundational questions.

14. For Intermediate, ask moderately challenging questions.

15. For Experienced, ask advanced professional questions.

16. Do not provide the answer.

17. Do not provide hints or explanations.

18. Do not generate multiple questions.

19. The student profile and career context are provided
    for background only. They must not change the
    selected subject or determine question examples.

20. Do not assume the student belongs to IT or programming.

21. Do not introduce unrelated industries, businesses,
    products or scenarios into a question.

22. Use practical scenarios only when they are directly
    relevant to the selected subject.

23. Use coding questions only when coding is relevant
    to the selected subject.

24. Make every question clear, concise and appropriate
    for the selected level.

25. Return ONLY valid JSON in the required format.



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

# JOB & INTERNSHIP RECOMMENDATION PAGE

def job_internship_recommendation(request):

    if not request.user.is_authenticated:
        return redirect("login")

    return render(
        request,
        "job_internship_recommendation.html"
    )
# JOB & INTERNSHIP PROFILE ANALYSIS PAGE

# @login_required(login_url='login')

# def career_aptitude_quiz(request):
#     return render(request, 'CareerPathApp/career_aptitude_quiz.html')

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

    # LOGIN CHECK

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "message": "Login required."
            },
            status=401
        )

    try:

        # READ REQUEST DATA

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

PROFILE SUMMARY

Write a concise, professional profile summary based strictly on
the student's Education, Selected Interest, and Entered Skills.

The summary should:
- Clearly describe the student's current professional profile.
- Mention the relevant education background naturally.
- Mention the selected interest/domain.
- Highlight the student's existing skills that are relevant to that domain.
- Show the student's potential career direction.
- Sound like a professional resume/profile summary.
- Be specific to the student's actual information.
- Do NOT add skills that the student did not enter.
- Do NOT assume a Technology/IT career from MCA or any other education alone.
- Do NOT use exaggerated claims such as "highly skilled", "expert",
  "industry-ready", or "experienced" unless explicitly supported.
- Keep the summary concise: 2–4 professional sentences.
- Avoid generic or repetitive statements.

============================================================
2. INTEREST ALIGNMENT
============================================================

INTEREST ALIGNMENT

Write a concise, professional explanation of how the student's
entered skills and selected interest are connected.

The explanation should:
- Clearly explain the relationship between the student's current
  skills and selected interest.
- Mention only skills that the student actually entered.
- Explain how those skills support the selected interest or career direction.
- Identify the strength of alignment based on the provided information.
- Be specific to the student's actual interest and skills.
- Do NOT add or assume skills that were not entered.
- Do NOT assume a Technology/IT connection from education alone.
- Do NOT introduce unrelated professional domains.
- Do NOT use exaggerated claims such as "perfect match",
  "excellent expertise", or "guaranteed career".
- Keep it professional, concise, and realistic.
- Write 2–3 sentences.

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
Identify only genuinely useful ADDITIONAL skills or competencies
that are missing from the student's entered skills and would help
with the selected interest and suitable career direction.

Generate these dynamically based on:
- Selected Interest
- Entered Skills
- Career Direction

IMPORTANT RULES:

- Treat all skills entered by the student as already-existing skills.
- Do NOT include any skill that is already present.
- Do NOT create a modified version of an existing skill.
- Do NOT simply add words such as "Technique", "Advanced",
  "Fundamentals", "Basics", or "Improvement" to an existing skill.
- For example, if the student has "Batting", do NOT return
  "Batting Technique".
- If the student has "Bowling", do NOT return
  "Bowling Technique".
- Generate only genuinely NEW skills that complement the
  student's existing skills.
- Every skill gap must be directly useful for the selected
  interest and suitable career direction.
- Do NOT use a fixed list.
- Do NOT introduce unrelated domain skills based only on education.
- Avoid generic filler skills.
- Return only 3–6 meaningful skill gaps.
Skill gaps must be based on the student's actual interest and
existing skills, without assuming a specific profession such as
coach, trainer, analyst, instructor, or performance specialist
unless the student's information clearly supports that direction.
# ============================================================
# 5. CAREER FOCUS
# ============================================================

Generate between 3 and 6 suitable career roles.

Career roles must be based on the student's ACTUAL
selected interest and ACTUAL entered skills.

Education is supporting information only.
Do NOT let education alone determine the career domain.

============================================================
STRICT CAREER DOMAIN RULE
============================================================

First identify the domain represented by the student's
SELECTED INTEREST.

Then verify whether the ENTERED SKILLS actually support
a career role in that domain.

A career role must be directly or reasonably supported by
the student's entered skills.

Do NOT introduce a completely new professional domain
only because it is commonly associated with the interest.

============================================================
IMPORTANT EXAMPLES
============================================================

Example 1:

Education:
MCA

Interest:
Cricket

Skills:
Bowling, Batting

Suitable career direction may include roles related to:

- Cricket Coaching
- Bowling Coaching
- Batting Coaching
- Cricket Training
- Cricket Performance

Do NOT automatically introduce:

- Data Analyst
- Sports Data Analyst
- Data Scientist
- Software Developer
- Python Developer
- IT Analyst

because the student did NOT enter data, analytics,
programming or software-related skills.

------------------------------------------------------------

Example 2:

Education:
MCA

Interest:
Biology

Skills:
Biology, Research

Suitable career direction may include roles related to:

- Biological Research
- Laboratory Research
- Life Sciences Research
- Biology Research Assistance
- Scientific Research

Do NOT automatically introduce Software Developer,
Python Developer or Data Analyst unless the student's
entered skills actually support those roles.

------------------------------------------------------------

Example 3:

Education:
BCom

Interest:
Finance

Skills:
Accounting, Excel, Financial Analysis

Finance and accounting-related career roles are
appropriate because the entered skills support them.

------------------------------------------------------------

Example 4:

Education:
MCA

Interest:
Python Development

Skills:
Python, Django, SQL

Technology-related career roles are appropriate because
the student's actual interest and skills support Technology.

============================================================
STRICT RULES
============================================================

1. Do NOT use a fixed career list.

2. Do NOT assume Technology is the default domain.

3. Do NOT assume MCA means Technology.

4. Do NOT assume BSc means Science-related career.

5. Do NOT assume BCom means Accounting.

6. Do NOT assume BA means Arts-related career.

7. Do NOT introduce Data/Analytics roles unless the entered
   skills actually contain relevant data/analytics abilities.

8. Do NOT introduce Programming/IT roles unless the entered
   skills actually contain relevant programming/IT abilities.

9. Do NOT introduce Management roles unless the entered
   interest and skills support management.

10. Do NOT introduce Research roles unless the entered
    interest or skills support research.

11. Do NOT introduce a new technical field merely because
    the student's education is MCA, BCA, CS or another
    technology-related degree.

12. The student's entered skills are the strongest evidence
    for deciding whether a specific career role is suitable.

13. Do NOT invent skills that the student did not enter.

14. Do NOT recommend a role that requires a completely
    different skill domain from the student's entered skills.

15. Career roles must change when the student's interest
    or skills change.

16. Keep recommendations realistic for a student/fresher.

17. Do NOT simply return the selected interest as a career.

18. Do NOT repeat the same career roles for every student.

============================================================
FINAL VALIDATION BEFORE OUTPUT
============================================================

Before returning each career role, verify:

- Is it related to the selected interest?
- Is it supported by the entered skills?
- Does it avoid introducing an unrelated domain?
- Is it reasonable for a student/fresher?

If a career role fails any of these checks,
DO NOT include it.

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

    # JOb Internship Opportunity 

def job_internship_opportunity(request):

    if not request.user.is_authenticated:
        return redirect("login")

    return render(
        request,
        "job_internship_opportunity.html"
    )
# API
def job_internship_opportunity_api(request):

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "error": "Login required."
            },
            status=401
        )

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "POST request required."
            },
            status=405
        )

    try:
        data = json.loads(request.body)

        interest = data.get("interest", "").strip()
        skills = data.get("skills", "").strip()
        education = data.get("education", "").strip()
        experience = data.get("experience", "").strip()

        if not interest:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Interest is required."
                },
                status=400
            )

        if not skills:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Skills are required."
                },
                status=400
            )

        if not education:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Education is required."
                },
                status=400
            )

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Gemini API key not configured."
                },
                status=500
            )

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an intelligent AI career opportunity recommendation system.

Your task is to generate dynamic job and internship opportunities
ONLY from the user's actual profile.

USER PROFILE:

Interest:
{interest}

Skills:
{skills}

Education:
{education}

Experience:
{experience}

CORE RULE:

The user's Interest, Skills, and Education are the ONLY source
for deciding suitable opportunities.

Every time the input changes, the recommended opportunities
MUST change accordingly.

Do NOT use fixed, predefined, or previously generated opportunities.


FIELD-AGNOSTIC REQUIREMENT:

The system must work for ANY career field.

Do NOT assume:
- Technology
- IT
- Software
- Python
- Computer Science
- Web Development

unless these are actually present in the user's Interest or Skills.


INTEREST RULE:

Interest is the PRIMARY factor for selecting the opportunity domain.

Skills are used to determine whether the user matches that opportunity.

Education is used mainly for eligibility.

Do NOT generate an opportunity only because of the education.


EXAMPLES:

If:

Interest = Cricket
Skills = Batting, Bowling, Fitness
Education = MCA

Then recommend cricket/sports-related opportunities.

Do NOT recommend:
Python Developer
Backend Developer
Software Developer
Web Developer


If:

Interest = Biology
Skills = Research, Laboratory, Biology
Education = B.Sc Biology

Then recommend biology/life-science/research-related opportunities.


If:

Interest = Finance
Skills = Accounting, Excel, Financial Analysis
Education = B.Com

Then recommend finance/accounting-related opportunities.


If:

Interest = Teaching
Skills = Communication, Mathematics, Presentation
Education = B.Ed

Then recommend teaching/education-related opportunities.


If:

Interest = Python Development
Skills = Python, Django, SQL, REST API
Education = MCA

Then recommend Python/backend/software-related opportunities.


DYNAMIC OPPORTUNITIES:

Generate as many genuinely relevant opportunities as practical
for the user's profile.

There is NO fixed number of opportunities.
Do not limit recommendations to 10.

Return only opportunities that genuinely match the user's
Interest, Skills, Education, and Experience.

Do NOT generate unrelated opportunities to increase the count.

If only a few relevant opportunities exist, return only those.
Never assume the user belongs to the IT or technology field.



Each opportunity must be meaningfully different.

Do not simply change the job title while keeping the same
description and skills.


DYNAMIC DATA:

For EVERY opportunity, dynamically generate:

- title
- organization
- type
- description
- eligibility
- required_skills
- location
- salary_or_stipend
- duration
- deadline
- match_score
- match_reason
- apply_link


IMPORTANT FOR OPPORTUNITY DETAILS:

- Every opportunity must have details that are specific to that
  particular opportunity.
- Do NOT repeat the same location, salary/stipend, duration,
  or deadline for every opportunity.
- These fields must be independently generated according to the
  opportunity type and domain.
- If a realistic value cannot be determined, return null.
- Do not use "Not specified" in the JSON response. Use null instead.
- Do not invent verified real-world job information.
- For AI-generated opportunities, clearly treat salary, location,
  duration and deadline as estimated/example information unless
  they come from a real provided source.
  CURRENT DATE RULES:

- The current year is 2026.
- Never generate a deadline from 2023, 2024, or 2025.
- Every deadline must be a future date relative to the current date.
- Since the current date is October 2026, deadlines should be
  between October 2026 and December 2026.
- Use realistic future dates only.
- If a deadline cannot be reasonably determined, return null.

LOCATION RULES:

- Locations must be in India.
- Prefer Indian cities such as Indore, Bhopal, Pune, Mumbai,
  Bengaluru, Hyderabad, Delhi, Chennai, Ahmedabad, etc.
- Do not generate locations outside India.
- If the opportunity is suitable for remote work, use
  "Remote - India".
IMPORTANT:

The following fields MUST also depend on the actual opportunity:

description
eligibility
required_skills
duration
match_reason
match_score

Do NOT copy the user's skills blindly into every opportunity.

required_skills must represent skills actually relevant to
that particular opportunity.

match_score must represent the actual match between:

Interest + Skills + Education

and the generated opportunity.


REAL-WORLD DATA SAFETY:

Do not fabricate real companies or organizations.

Do not fabricate real salaries.

Do not fabricate real deadlines.

Do not fabricate application URLs.

If reliable information is unavailable, return null.

apply_link must be null unless a genuine application URL
is available from the provided information.

These are AI-generated career recommendations and must not
be presented as verified live job listings.


MATCH SCORE:

match_score must be an integer between 0 and 100.

Higher score means stronger alignment with the user's:

Interest + Skills + Education.


OUTPUT:

Return ONLY valid JSON.

JSON format:

{{
    "opportunities": [
        {{
            "title": "",
            "organization": null,
            "type": "",
            "description": "",
            "eligibility": "",
            "required_skills": [],
            "location": null,
            "salary_or_stipend": null,
            "duration": null,
            "deadline": null,
            "match_score": 0,
            "match_reason": "",
            "apply_link": null
        }}
    ]
}}
"""


        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        ai_result = json.loads(response.text)

        opportunities = ai_result.get(
            "opportunities",
            []
        )

        return JsonResponse(
            {
                "success": True,
                "interest": interest,
                "skills": skills,
                "education": education,
                "experience": experience,
                "opportunities": opportunities
            }
        )

    except Exception as e:

        print(
            "Opportunity API Error:",
            str(e)
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(e)
            },
            status=500
        )
