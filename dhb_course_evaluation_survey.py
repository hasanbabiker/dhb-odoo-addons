# -*- coding: utf-8 -*-
"""
DHB Course Evaluation Survey  ->  Odoo Survey
=============================================
يُشغَّل داخل odoo shell:

  docker exec -i odoo odoo shell -c /etc/odoo/odoo.conf \
      --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo \
      -d odoo --no-http < dhb_course_evaluation_survey.py

السكربت آمن للإعادة: لو الاستبيان موجود ولا توجد ردود عليه، يعيد بناءه.
لو فيه ردود فعلية يتوقف ولا يمس شيئاً.
"""

TITLE = "DHB Course Evaluation Survey — استبيان تقييم الدورة التدريبية"

# ---------------------------------------------------------------- helpers ---
def keep(model, vals):
    """أبقِ الحقول الموجودة فعلاً في هذه النسخة من Odoo فقط."""
    flds = env[model]._fields
    return {k: v for k, v in vals.items() if k in flds}


def answers(values):
    return [(0, 0, {"value": v, "sequence": i * 10}) for i, v in enumerate(values)]


# ------------------------------------------------------------ preconditions --
if "survey.survey" not in env:
    raise SystemExit("وحدة Survey غير مثبّتة. ثبّتها أولاً ثم أعد التشغيل.")

Survey = env["survey.survey"]

# ---------------------------------------------------------- course choices --
COURSES_FALLBACK = [
    "NEBOSH International General Certificate (English)",
    "شهادة النيبوش الدولية العامة (Arabic)",
    "NEBOSH International Diploma — Unit DI1",
    "NEBOSH International Diploma — Unit DI2",
    "NEBOSH International Diploma — Unit DI3",
    "IOSH Managing Safely",
    "IOSH Working Safely",
    "NEBOSH HSE Certificate",
    "NEBOSH Certificate in Fire Safety",
    "NEBOSH Environmental Management Certificate",
    "Other — أخرى",
]

courses = []
try:
    if "dhb.course" in env:
        courses = [c for c in env["dhb.course"].search([]).mapped("name") if c]
        if courses:
            courses.append("Other — أخرى")
except Exception:
    courses = []
if not courses:
    courses = COURSES_FALLBACK

# ---------------------------------------------------------------- content ---
LIKERT = [
    "Strongly Agree — أوافق تماماً",
    "Agree — أوافق",
    "Average — متوسط",
    "Disagree — أختلف",
    "Strongly Disagree — أختلف بشدة",
]

COURSE_ROWS = [
    "Had well written, clear, accurate, up-to-date and accessible learning material",
    "Sessions were structured and well organized",
    "Provided knowledge and skills relevant to my job / profession and/or personal objectives",
    "Assessments and feedbacks helped in learning progression",
]

TUTOR_ROWS = [
    "Goal and objectives of the course were clearly defined and explained",
    "Content and delivery are based on relevant and up-to-date knowledge of the subject",
    "Organized and well prepared; start and end on time",
    "Articulate and engaging. Encourages participation and questions",
    "Covered the material clearly and at an appropriate pace, using relevant examples and experience",
]

ADMIN_ROWS = [
    "Tools and systems were easy to use and accessible for all (e-learning platform and Zoom)",
    "The audio and visual connection was good",
    "Valuable information and advice were provided before the start of the course",
]

# ------------------------------------------------------- create / rebuild ---
existing = Survey.with_context(active_test=False).search([("title", "=", TITLE)])
if existing:
    survey = existing[0]
    inputs = env["survey.user_input"].search_count([("survey_id", "=", survey.id)])
    if inputs:
        raise SystemExit(
            "الاستبيان موجود وعليه %s ردّاً. لن يتم المساس به. "
            "احذفه يدوياً أو غيّر TITLE إن أردت نسخة جديدة." % inputs
        )
    survey.question_and_page_ids.unlink()
else:
    survey = Survey.create(keep("survey.survey", {"title": TITLE}))

survey.write(
    keep(
        "survey.survey",
        {
            "title": TITLE,
            "description": (
                "<p>Your feedback helps us improve our training. "
                "The survey is anonymous and takes about three minutes.<br/>"
                "ملاحظاتك تساعدنا على تطوير تدريبنا. الاستبيان غير مرتبط باسمك "
                "ويستغرق نحو ثلاث دقائق.</p>"
            ),
            "description_done": (
                "<p>Thank you. Your evaluation has been submitted and it helps us "
                "improve our training.<br/>شكراً لك، تم إرسال تقييمك وهو يساعدنا "
                "على تطوير تدريبنا.</p>"
            ),
            "access_mode": "public",
            "users_login_required": False,
            "questions_layout": "page_per_section",
            "progression_mode": "percent",
            "scoring_type": "no_scoring",
            "is_attempts_limited": False,
            "active": True,
        },
    )
)

Q = env["survey.question"]
seq = 0


def add(**vals):
    global seq
    seq += 10
    vals["survey_id"] = survey.id
    vals["sequence"] = seq
    return Q.create(keep("survey.question", vals))


def page(title):
    return add(title=title, is_page=True, question_type=False)


def matrix(title, rows):
    return add(
        title=title,
        question_type="matrix",
        matrix_subtype="simple",
        constr_mandatory=True,
        constr_error_msg="This question requires an answer — هذا السؤال مطلوب",
        matrix_row_ids=answers(rows),
        suggested_answer_ids=answers(LIKERT),
    )


def choice(title, options, mandatory=True):
    return add(
        title=title,
        question_type="simple_choice",
        constr_mandatory=mandatory,
        constr_error_msg="This question requires an answer — هذا السؤال مطلوب",
        suggested_answer_ids=answers(options),
    )


# 1 — General information
page("General Information — معلومات عامة")
choice("Training Course Name — اسم الدورة التدريبية", courses)
choice("Training Type — نوع التدريب", ["Face to Face — وجهاً لوجه", "Online — عبر الإنترنت"])

# 2 — The course
page("The Course — الدورة")
matrix("Please rate the following — يرجى تقييم العبارات التالية", COURSE_ROWS)

# 3 — The tutor
page("The Tutor — المدرب")
matrix("The tutor… — المدرب…", TUTOR_ROWS)

# 4 — Administration and facilities
page("Administration and Facilities — الإدارة والتجهيزات")
matrix("Please rate the following — يرجى تقييم العبارات التالية", ADMIN_ROWS)

# 5 — Closing questions
page("Closing Questions — أسئلة ختامية")
choice("This course was chosen by:", ["Me", "My company", "Both", "Other"])
choice("This course helped me improve my skills:", ["Yes", "May be", "No"])
choice("I would recommend this course to others:", ["Yes", "May be", "No"])
choice("The tutor delivered the NEBOSH specification and mode of assessments:", ["Yes", "No"])
add(
    title="Any further comments: — أي ملاحظات إضافية:",
    question_type="text_box",
    constr_mandatory=False,
)

env.cr.commit()

# ------------------------------------------------------------------ report --
base = env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
try:
    link = base + survey.get_start_url()
except Exception:
    link = "%s/survey/start/%s" % (base, survey.access_token)

pages = survey.question_and_page_ids.filtered("is_page")
qs = survey.question_and_page_ids - pages
print("")
print("survey id      :", survey.id)
print("pages          :", len(pages))
print("questions      :", len(qs))
print("course options :", len(courses))
print("public link    :", link)
print("backend        : %s/odoo/surveys/%s" % (base, survey.id))
print("")
for r in survey.question_and_page_ids.sorted("sequence"):
    if r.is_page:
        print("== %s" % r.title)
    else:
        n = len(r.matrix_row_ids) if r.question_type == "matrix" else len(r.suggested_answer_ids)
        print("   [%-14s] %2s | %s" % (r.question_type, n, r.title[:70]))
