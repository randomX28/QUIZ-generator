import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

ROLL_NO_REGEX = r"^[0-9]{2}[A-Z]{2}[0-9]{4}$"


# ── Question ──────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    text: str
    option_a: Optional[str] = ""
    option_b: Optional[str] = ""
    option_c: Optional[str] = ""
    option_d: Optional[str] = ""
    correct_opt: Optional[str] = ""           # full text of correct answer (optional for subjective)
    pool_id: int = Field(..., ge=1)
    bank_id: Optional[int] = 1
    topic: Optional[str] = None
    question_type: Optional[str] = "objective" # "objective" or "subjective"
    marks: Optional[int] = 2                  # custom marks for this question
    difficulty: Optional[str] = "MEDIUM"      # "EASY", "MEDIUM", "HARD"
    co_tag: Optional[str] = ""                # e.g. "CO1", "CO2"


class QuestionOut(QuestionCreate):
    id: int
    times_used: int
    created_at: str


# ── Banks & Pools ─────────────────────────────────────────────────────────────

class BankCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    code: Optional[str] = Field(None, description="Paper code prefix, e.g. CD (auto-derived from name if blank)")
    subject_name: Optional[str] = ""
    course_code: Optional[str] = ""
    num_pools: Optional[int] = Field(5, ge=1, le=100, description="Number of empty pools to create")


class PoolCreate(BaseModel):
    name: Optional[str] = ""


# ── Paper ─────────────────────────────────────────────────────────────────────

DEFAULT_SUBJECT_NAME = "Compiler Design"
DEFAULT_COURSE_CODE = "NCSC302"

DEFAULT_QUIZ_TITLE = "Quiz 1"
DEFAULT_SEMESTER_TITLE = "End Semester Examination"

DEFAULT_QUIZ_MARKS = "10 (2 marks per question)"
DEFAULT_SEMESTER_MARKS = "50 (10 marks per question)"

DEFAULT_QUIZ_DURATION = "30 Minutes"
DEFAULT_SEMESTER_DURATION = "3 Hours"

DEFAULT_QUIZ_INSTRUCTIONS = "(i) Tick the correct option for each question (ii) All questions carry 2 marks each"
DEFAULT_SEMESTER_INSTRUCTIONS = "(i) Answer all questions in the provided answer booklet (ii) All questions carry equal marks"

# Backward compatibility alias
DEFAULT_DURATION = DEFAULT_QUIZ_DURATION
DEFAULT_INSTRUCTIONS = DEFAULT_QUIZ_INSTRUCTIONS


class GenerateRequest(BaseModel):
    count: int = Field(1, ge=1, le=200, description="Number of papers to generate")
    bank_id: Optional[int] = Field(1, description="Question bank to draw questions from")
    pool_ids: Optional[List[int]] = Field(None, description="Pools to draw from (default: all pools of the bank)")
    per_pool: Optional[Dict[int, int]] = Field(None, description="Optional manual questions-per-pool override {pool_no: n}")
    questions_per_paper: Optional[int] = Field(5, ge=1, le=500, description="Number of questions per paper")
    paper_type: Optional[str] = Field("objective", description="'objective' (Quiz) or 'subjective' (Semester Paper)")
    subject_name: Optional[str] = Field(DEFAULT_SUBJECT_NAME, description="Subject name")
    course_code: Optional[str] = Field(DEFAULT_COURSE_CODE, description="Course code")
    exam_title: Optional[str] = Field(None, description="Exam title (e.g. 'Quiz 1' or 'End Semester Examination')")
    max_marks: Optional[str] = Field(None, description="Max marks line")
    marks_per_question: Optional[str] = Field(None, description="Optional marks per question (e.g. '2 Marks' or '10 Marks')")
    exam_date: Optional[str] = Field(None, description="Exam date (e.g. '06-Sept-2026')")
    duration: Optional[str] = Field(None, description="Exam duration")
    randomize: Optional[bool] = Field(True, description="Whether to randomize question selection, order and options")
    use_default_instructions: Optional[bool] = Field(True, description="Whether to use default instructions")
    instructions: Optional[str] = Field(None, description="Custom instructions if use_default_instructions is False")


class PaperQuestion(BaseModel):
    q_index: int               # position on paper (0-based)
    question_id: int
    text: str
    shuffled_options: Optional[Dict[str, str]] = {}   # {'a': text, 'b': text, ...} or empty for subjective
    correct_opt: Optional[str] = ""                   # stored for grading (if objective)
    marks: Optional[int] = 2                          # custom marks for this question


class PaperOut(BaseModel):
    uid: str
    paper_no: Optional[int] = None
    created_at: str
    subject_name: Optional[str] = DEFAULT_SUBJECT_NAME
    course_code: Optional[str] = DEFAULT_COURSE_CODE
    duration: Optional[str] = DEFAULT_QUIZ_DURATION
    instructions: Optional[str] = DEFAULT_QUIZ_INSTRUCTIONS
    paper_type: Optional[str] = "objective"
    exam_title: Optional[str] = DEFAULT_QUIZ_TITLE
    max_marks: Optional[str] = DEFAULT_QUIZ_MARKS
    marks_per_question: Optional[str] = ""
    exam_date: Optional[str] = ""
    is_randomized: Optional[bool] = True
    questions: List[PaperQuestion]


# ── Grading ───────────────────────────────────────────────────────────────────

class GradeRequest(BaseModel):
    roll_no: str
    paper_uid: str
    responses: Dict[int, str]  # {q_index(0-4): chosen_label('a'/'b'/'c'/'d')}
    entered_by: Optional[str] = "TA"

    @field_validator("roll_no")
    @classmethod
    def validate_roll_no(cls, v: str) -> str:
        clean = v.strip().upper()
        if not re.match(ROLL_NO_REGEX, clean):
            raise ValueError(
                f"Invalid Roll Number '{v}'. Format must be: 2 digits, 2 uppercase letters, 4 digits (e.g. 21CS0001)."
            )
        return clean


class QuestionResult(BaseModel):
    q_index: int
    question_text: str
    chosen_text: str
    correct_text: str
    is_correct: bool


class GradeResponse(BaseModel):
    roll_no: str
    paper_uid: str
    score: int
    total: int
    breakdown: List[QuestionResult]


# ── Results ───────────────────────────────────────────────────────────────────

class StudentResult(BaseModel):
    id: int
    roll_no: str
    paper_uid: str
    score: int
    total: int = 5
    breakdown: List[Dict[str, Any]]
    entered_by: str
    entered_at: str
