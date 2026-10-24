import io
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from gtts import gTTS
from openai import (APIConnectionError, InternalServerError, NotFoundError, OpenAI,
                    PermissionDeniedError, RateLimitError)
from grammar_tables import render_grammar_tables
from storage import LocalStore


# ============================================================
# GERMAN MASTER COACH — free German coach (A1 → B2) for non-commercial use
# License: PolyForm Noncommercial 1.0.0 (see LICENSE)
# Streamlit + Gemini, data saved locally (data/ folder) or in Supabase
# ============================================================
#
# Features:
# - 8 stages from A1 to B2, each with topics for Grammar, Vocabulary,
#   Listening, Reading, Writing and Speaking.
# - A1/A2: all explanations, instructions and feedback in English
#   (German examples with translations). B1: German with English hints.
#   B2: German only.
# - Lessons, exercises and grading by Gemini; automatic promotion by your
#   chosen rule: a percentage, or the Goethe standard (60% in each of
#   Reading, Listening, Writing and Speaking).
# - Two ways to run it: LOCAL (data in the data/ folder on your computer,
#   only reachable from your computer) or CLOUD (Supabase + Streamlit Cloud).
# - Study Hub: week-by-week plan, grammar checklist per level, Gemini
#   vocabulary lists with a daily vocab check, grammar reference tables.
#
# Setup: see README.md.
#   Local: run start_local.bat (Windows) or start_local.sh (Mac/Linux) and
#          paste your Gemini key once. Nothing else needed.
#   Cloud: Streamlit secrets (Streamlit Cloud → Settings → Secrets):
#     GEMINI_API_KEY = "..."
#     SUPABASE_URL   = "https://xxxx.supabase.co"   # cloud mode only
#     SUPABASE_KEY   = "..."        # Supabase secret key (service_role)
#     APP_PASSWORD   = "..."        # optional, recommended for public URLs
#     GEMINI_MODEL   = "gemini-3.8-flash"   # optional
#     LEARNER_ID     = "me"         # optional
# ============================================================


st.set_page_config(
    page_title="🇩🇪 German Master Coach",
    page_icon="🇩🇪",
    layout="wide",
)


# -----------------------------
# Configuration
# -----------------------------
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LOCAL_SETTINGS = APP_DIR / "data" / "settings.json"


def setting(name: str, default: str = "") -> str:
    """Streamlit secrets first, then (local mode) data/settings.json."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:  # no secrets file at all: fine in local mode
        pass
    try:
        return str(json.loads(LOCAL_SETTINGS.read_text(encoding="utf-8")).get(name) or default)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


GEMINI_API_KEY = setting("GEMINI_API_KEY")
SUPABASE_URL = setting("SUPABASE_URL")
SUPABASE_KEY = setting("SUPABASE_KEY")
GEMINI_MODEL = setting("GEMINI_MODEL", "gemini-3.8-flash")
LEARNER_ID = setting("LEARNER_ID", "me")
APP_PASSWORD = setting("APP_PASSWORD")
# "cloud" when Supabase is configured, otherwise "local" (data/ folder on this computer).
STORAGE_MODE = setting("STORAGE", "cloud" if (SUPABASE_URL and SUPABASE_KEY) else "local").lower()

# Models shown in the sidebar (IDs from the Gemini API model list).
MODEL_OPTIONS = {
    "Gemini 3.8 Flash (best)": "gemini-3.8-flash",
    "Gemini 3.6 Flash": "gemini-3.6-flash",
    "Gemini 3.5 Flash-Lite (fast, cheap)": "gemini-3.5-flash-lite",
    "Gemini 3.1 Flash-Lite (cheapest)": "gemini-3.1-flash-lite",
    "Gemini 3.1 Pro (preview, slow)": "gemini-3.1-pro-preview",
    "Gemini 2.5 Flash (legacy)": "gemini-2.5-flash",
}
FALLBACK_MODEL = "gemini-3.5-flash-lite"

# Optional custom model ID from Streamlit Secrets.
CUSTOM_GEMINI_MODEL = setting("CUSTOM_GEMINI_MODEL").strip()
if CUSTOM_GEMINI_MODEL and CUSTOM_GEMINI_MODEL not in MODEL_OPTIONS.values():
    MODEL_OPTIONS[f"Custom — {CUSTOM_GEMINI_MODEL}"] = CUSTOM_GEMINI_MODEL

if not GEMINI_API_KEY:
    if STORAGE_MODE == "local":
        # First start on this computer: ask for the key once and keep it in data/settings.json.
        st.title("🇩🇪 German Personal Tutor: first-time setup")
        st.write(
            "The coach uses Google's **Gemini** AI. Get a free API key at "
            "[aistudio.google.com](https://aistudio.google.com) → **Get API key** → **Create API key**, "
            "then paste it here. It is saved only on this computer (in `data/settings.json`)."
        )
        new_key = st.text_input("Gemini API key", type="password")
        if st.button("Save and start", type="primary", disabled=not new_key.strip()):
            LOCAL_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            current = {}
            if LOCAL_SETTINGS.exists():
                try:
                    current = json.loads(LOCAL_SETTINGS.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    current = {}
            current["GEMINI_API_KEY"] = new_key.strip()
            LOCAL_SETTINGS.write_text(json.dumps(current, indent=1), encoding="utf-8")
            st.rerun()
        st.stop()
    st.error("Missing GEMINI_API_KEY in your Streamlit secrets. See README.md → Cloud setup, Step 2.")
    st.stop()

if STORAGE_MODE == "cloud" and (not SUPABASE_URL or not SUPABASE_KEY):
    st.error("Cloud mode needs SUPABASE_URL and SUPABASE_KEY in your Streamlit secrets. "
             "See README.md → Cloud setup, Step 3. (Or remove STORAGE = \"cloud\" to run locally.)")
    st.stop()

# Optional password: keeps strangers from using your app (and your Gemini quota).
if APP_PASSWORD and not st.session_state.get("app_unlocked"):
    import hmac

    st.title("🇩🇪 German Master Coach")
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, APP_PASSWORD):
            st.session_state.app_unlocked = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()


# -----------------------------
# Clients
# -----------------------------
@st.cache_resource
def get_supabase():
    """The database: Supabase in cloud mode, JSON files in data/ in local mode.
    Both offer the same table().select()/insert()/upsert()/delete() calls."""
    if STORAGE_MODE == "local":
        return LocalStore(APP_DIR / "data")
    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_resource
def get_llm() -> OpenAI:
    # Gemini provides an OpenAI-compatible endpoint.
    return OpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


supabase = get_supabase()
llm = get_llm()

# Cloud mode: fail early with a clear message if Supabase is unreachable
# (e.g. free-tier project paused, or wrong SUPABASE_URL).
try:
    if STORAGE_MODE == "cloud":
        supabase.table("learner_progress").select("learner_id").limit(1).execute()
except Exception as exc:
    st.error(
        "Cannot connect to Supabase. If you are on the free tier, your project "
        "may be paused — open supabase.com/dashboard and click 'Restore project'. "
        "Also check SUPABASE_URL in Streamlit Secrets."
    )
    st.caption(f"Technical detail: {type(exc).__name__}")
    st.stop()


# -----------------------------
# Curriculum
# -----------------------------
SKILL_MODES = ["Grammar", "Vocabulary", "Listening", "Reading", "Writing", "Speaking"]

# `topics` is the stage overview (used by Auto and the roadmap).
# `skill_topics` gives every skill its own topics for that stage, so that
# Vocabulary/Listening/etc. never fall back to pure grammar.
CURRICULUM: List[Dict[str, Any]] = [
    {
        "stage": 1,
        "level": "A1",
        "title": "German Basics",
        "weeks": "1–8",
        "topics": [
            "sein and haben",
            "present tense of regular verbs",
            "W-questions and yes/no questions",
            "articles der, die, das and ein",
            "plural of nouns",
            "negation with nicht and kein",
            "Akkusativ basics",
        ],
        "skill_topics": {
            "Grammar": [
                "sein and haben",
                "present tense of regular verbs",
                "W-questions and yes/no questions",
                "articles der, die, das and ein",
                "plural of nouns",
                "negation with nicht and kein",
                "Akkusativ basics",
            ],
            "Vocabulary": [
                "greetings and introductions",
                "numbers, time and dates",
                "family and friends",
                "food and drinks",
                "the city and directions",
                "things at home",
            ],
            "Listening": [
                "greetings and introductions",
                "numbers and prices",
                "simple questions and answers",
                "short announcements",
            ],
            "Reading": [
                "signs and notices",
                "simple forms",
                "short messages",
                "menus and price lists",
            ],
            "Writing": [
                "filling in a form",
                "introducing yourself in writing",
                "short personal messages",
            ],
            "Speaking": [
                "introducing yourself",
                "asking for prices and times",
                "ordering food and drinks",
                "talking about your family",
            ],
        },
    },
    {
        "stage": 2,
        "level": "A2",
        "title": "Everyday German",
        "weeks": "9–16",
        "topics": [
            "Perfekt with haben and sein",
            "modal verbs",
            "separable verbs",
            "Dativ basics",
            "possessive articles",
            "prepositions of place and time",
            "imperative",
        ],
        "skill_topics": {
            "Grammar": [
                "Perfekt with haben and sein",
                "modal verbs",
                "separable verbs",
                "Dativ basics",
                "possessive articles",
                "prepositions of place and time",
                "imperative",
            ],
            "Vocabulary": [
                "daily routine",
                "clothes and shopping",
                "weather and seasons",
                "hobbies and free time",
                "the body and health basics",
                "transport and directions",
            ],
            "Listening": [
                "everyday conversations",
                "phone messages",
                "train and station announcements",
                "talking about the past weekend",
            ],
            "Reading": [
                "short emails",
                "ads and timetables",
                "simple descriptions",
                "invitations",
            ],
            "Writing": [
                "short emails to friends",
                "invitations and replies",
                "describing your weekend",
            ],
            "Speaking": [
                "talking about your daily routine",
                "shopping conversations",
                "making appointments",
                "talking about the past",
            ],
        },
    },
    {
        "stage": 3,
        "level": "A2.2 → B1",
        "title": "B1 Core Consolidation",
        "weeks": "17–22",
        "topics": [
            "word order",
            "main clause vs subordinate clause",
            "Akkusativ and Dativ",
            "common prepositions",
            "modal verbs",
            "separable verbs",
            "Perfekt and Präteritum basics",
        ],
        "skill_topics": {
            "Grammar": [
                "word order",
                "main clause vs subordinate clause",
                "Akkusativ and Dativ",
                "common prepositions",
                "modal verbs",
                "separable verbs",
                "Perfekt and Präteritum basics",
            ],
            "Vocabulary": [
                "daily routine and free time",
                "food and shopping",
                "home and living",
                "health and body",
                "work and jobs",
                "travel and transport",
            ],
            "Listening": [
                "short everyday dialogues",
                "announcements and messages",
                "phone calls and appointments",
                "talking about the weekend",
            ],
            "Reading": [
                "short emails and notes",
                "ads and notices",
                "simple everyday texts",
                "short personal stories",
            ],
            "Writing": [
                "informal emails to friends",
                "short messages and notes",
                "describing your day",
                "writing about past events",
            ],
            "Speaking": [
                "introducing yourself",
                "talking about your daily routine",
                "making plans and appointments",
                "describing past experiences",
            ],
        },
    },
    {
        "stage": 4,
        "level": "B1",
        "title": "Everyday German & Communication",
        "weeks": "23–28",
        "topics": [
            "appointments",
            "housing",
            "workplace communication",
            "university life",
            "shopping",
            "travel",
            "describing problems",
            "giving opinions",
        ],
        "skill_topics": {
            "Grammar": [
                "dass, weil and wenn clauses",
                "two-way prepositions",
                "adjective endings",
                "Perfekt vs Präteritum in context",
                "verbs with prepositions",
            ],
            "Vocabulary": [
                "appointments",
                "housing",
                "workplace communication",
                "university life",
                "shopping",
                "travel",
            ],
            "Listening": [
                "appointments",
                "travel",
                "workplace communication",
                "describing problems",
            ],
            "Reading": [
                "housing",
                "university life",
                "shopping",
                "travel",
            ],
            "Writing": [
                "describing problems",
                "giving opinions",
                "appointments",
                "workplace communication",
            ],
            "Speaking": [
                "giving opinions",
                "describing problems",
                "appointments",
                "shopping",
            ],
        },
    },
    {
        "stage": 5,
        "level": "B1+",
        "title": "Complex Grammar",
        "weeks": "29–36",
        "topics": [
            "relative clauses",
            "Konjunktiv II",
            "passive voice",
            "comparatives",
            "reflexive constructions",
            "advanced conjunctions",
            "indirect questions",
        ],
        "skill_topics": {
            "Grammar": [
                "relative clauses",
                "Konjunktiv II",
                "passive voice",
                "comparatives",
                "reflexive constructions",
                "advanced conjunctions",
                "indirect questions",
            ],
            "Vocabulary": [
                "feelings and relationships",
                "media and technology",
                "environment",
                "education and career",
            ],
            "Listening": [
                "radio interviews",
                "everyday conversations with complex sentences",
                "explanations and instructions",
            ],
            "Reading": [
                "short newspaper articles",
                "blog posts",
                "instructions and rules",
            ],
            "Writing": [
                "semi-formal emails",
                "describing wishes and hypothetical situations",
                "describing processes",
            ],
            "Speaking": [
                "talking about wishes and hypotheticals",
                "comparing options",
                "explaining processes",
            ],
        },
    },
    {
        "stage": 6,
        "level": "B1+ → B2",
        "title": "B2 Transition",
        "weeks": "37–44",
        "topics": [
            "argumentation",
            "advanced connectors",
            "nominalisation",
            "formal language",
            "professional vocabulary",
            "summaries",
            "paraphrasing",
        ],
        "skill_topics": {
            "Grammar": [
                "advanced connectors",
                "nominalisation",
                "Konjunktiv I for reported speech",
                "participle attributes",
            ],
            "Vocabulary": [
                "professional vocabulary",
                "formal language",
                "argumentation",
                "advanced connectors",
            ],
            "Listening": [
                "argumentation",
                "workplace discussions",
                "podcast excerpts",
            ],
            "Reading": [
                "summaries",
                "argumentation",
                "opinion articles",
            ],
            "Writing": [
                "summaries",
                "paraphrasing",
                "argumentation",
                "formal language",
            ],
            "Speaking": [
                "argumentation",
                "paraphrasing",
                "professional vocabulary",
            ],
        },
    },
    {
        "stage": 7,
        "level": "B2",
        "title": "B2 Production",
        "weeks": "45–52",
        "topics": [
            "formal emails",
            "reports",
            "presentations",
            "debates",
            "professional conversations",
            "long-form speaking",
            "advanced listening",
        ],
        "skill_topics": {
            "Grammar": [
                "formal register",
                "alternatives to the passive",
                "complex sentence structure",
                "Konjunktiv I",
            ],
            "Vocabulary": [
                "professional conversations",
                "presentations",
                "reports",
                "formal emails",
            ],
            "Listening": [
                "advanced listening",
                "presentations",
                "professional conversations",
            ],
            "Reading": [
                "reports",
                "formal emails",
                "professional articles",
            ],
            "Writing": [
                "formal emails",
                "reports",
            ],
            "Speaking": [
                "presentations",
                "debates",
                "professional conversations",
                "long-form speaking",
            ],
        },
    },
    {
        "stage": 8,
        "level": "B2",
        "title": "B2 Exam & Fluency",
        "weeks": "53–64",
        "topics": [
            "Goethe-style reading",
            "Goethe-style listening",
            "Goethe-style writing",
            "Goethe-style speaking",
            "timed mock tests",
            "error elimination",
            "fluency maintenance",
        ],
        "skill_topics": {
            "Grammar": [
                "error elimination",
                "exam grammar review",
            ],
            "Vocabulary": [
                "fluency maintenance",
                "exam topic vocabulary",
            ],
            "Listening": [
                "Goethe-style listening",
                "timed mock tests",
            ],
            "Reading": [
                "Goethe-style reading",
                "timed mock tests",
            ],
            "Writing": [
                "Goethe-style writing",
                "error elimination",
            ],
            "Speaking": [
                "Goethe-style speaking",
                "fluency maintenance",
            ],
        },
    },
]

# How each skill should be TAUGHT (lesson) — keeps non-grammar modes
# from turning into grammar lessons.
MODE_TEACHING_STYLE = {
    "Grammar": (
        "Teach the grammar rule: forms, word order, and contrasts with clear examples."
    ),
    "Vocabulary": (
        "Teach 8–12 useful words and phrases for this topic. Put each word in "
        "`rules` as plain text like 'der Termin, die Termine — appointment'. "
        "For nouns ALWAYS give the article and plural. Use `examples` to show "
        "the words in natural sentences. Do NOT teach a grammar rule."
    ),
    "Listening": (
        "Teach listening strategies for this situation and the key phrases the "
        "learner will hear (in `rules`). Put a natural German dialogue or "
        "announcement of 60–120 words in `sample_text`; it will be played as "
        "audio. Do NOT teach a grammar rule."
    ),
    "Reading": (
        "Teach reading strategies and key vocabulary for this text type (in "
        "`rules`). Put a short authentic-style German text of 80–150 words in "
        "`sample_text`. Do NOT teach a grammar rule."
    ),
    "Writing": (
        "Teach how to write this text type: structure, opening, body, and "
        "closing phrases (Redemittel) in `rules`. Put a short model text in "
        "`sample_text`. Do NOT teach a grammar rule."
    ),
    "Speaking": (
        "Teach useful phrases (Redemittel) for this speaking situation in "
        "`rules`, and put a short model answer the learner could say in "
        "`sample_text`. Do NOT teach a grammar rule."
    ),
}


# -----------------------------
# Helper functions
# -----------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_stage(stage_no: int) -> Dict[str, Any]:
    return CURRICULUM[max(1, min(stage_no, len(CURRICULUM))) - 1]


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pct(value: float) -> int:
    return max(0, min(100, round(value)))


def normalize_answer(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def language_rules(stage_number: int) -> str:
    """How much English the coach uses: English at A1/A2, hints at B1, German at B2."""
    level = str(get_stage(stage_number)["level"])
    if level.startswith("A"):
        return (
            "LANGUAGE OF INSTRUCTION — MANDATORY: the learner is a beginner (" + level + ") and cannot "
            "read German instructions yet. Write ALL explanations, rules, task instructions, tips and "
            "feedback in simple English. Follow every German word or sentence you use as an example with "
            "its English translation in brackets. In exercises, state the task in English first; only the "
            "German the learner must work with is in German."
        )
    if level.startswith("B1"):
        return (
            "LANGUAGE OF INSTRUCTION: write explanations and instructions in simple German. Add a short "
            "English hint in brackets after difficult words, rules and task instructions."
        )
    return "LANGUAGE OF INSTRUCTION: use German only, at the learner's level."


def get_mode_topics(stage: Dict[str, Any], mode: str) -> List[str]:
    """Topics for one skill inside one stage. Auto uses the stage overview."""
    if mode in SKILL_MODES:
        topics = (stage.get("skill_topics") or {}).get(mode) or []
        if topics:
            return list(topics)
    return list(stage.get("topics") or []) or ["general German"]


def all_stage_topics(stage: Dict[str, Any]) -> List[str]:
    """Every topic that belongs to a stage, across all skills."""
    topics = list(stage.get("topics") or [])
    for skill_list in (stage.get("skill_topics") or {}).values():
        for topic in skill_list:
            if topic not in topics:
                topics.append(topic)
    return topics


def parse_json_from_model(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object even if the model wraps it in markdown."""
    text = text.strip()

    # Direct parse
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    # Markdown fenced JSON
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(1))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass

    # First object-looking block
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def call_llm(
    messages: List[Dict[str, str]],
    temperature: float = 0.4,
) -> str:
    selected_model = st.session_state.get("gemini_model", GEMINI_MODEL)
    # Tried in order when a model is overloaded (503), rate-limited, or unavailable.
    models = [selected_model] + [m for m in ("gemini-3.6-flash", FALLBACK_MODEL) if m != selected_model]
    for i, model in enumerate(models):
        try:
            response = llm.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=90,
            )
            if model != selected_model:
                st.toast(f"`{selected_model}` was busy or unavailable — `{model}` answered instead.")
            return response.choices[0].message.content or ""
        except (NotFoundError, PermissionDeniedError, InternalServerError,
                RateLimitError, APIConnectionError):
            if i == len(models) - 1:
                raise
    return ""


# -----------------------------
# Supabase data layer
# -----------------------------
def load_progress() -> Dict[str, Any]:
    result = (
        supabase.table("learner_progress")
        .select("*")
        .eq("learner_id", LEARNER_ID)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    initial = {
        "learner_id": LEARNER_ID,
        "current_stage": 1,
        "stage_mastery": 0,
        "overall_mastery": 0,
        "total_study_minutes": 0,
        "lifetime_attempts": 0,
        "lifetime_correct": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "last_study_date": None,
        "weak_areas": [],
        "status": "On Track",
        "updated_at": utc_now_iso(),
    }

    supabase.table("learner_progress").upsert(
        initial,
        on_conflict="learner_id",
    ).execute()

    return initial


def save_progress(progress: Dict[str, Any]) -> None:
    payload = dict(progress)
    payload["learner_id"] = LEARNER_ID
    payload["updated_at"] = utc_now_iso()

    supabase.table("learner_progress").upsert(
        payload,
        on_conflict="learner_id",
    ).execute()


def get_recent_attempts(limit: int = 30) -> List[Dict[str, Any]]:
    result = (
        supabase.table("exercise_attempts")
        .select("*")
        .eq("learner_id", LEARNER_ID)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_recent_mistakes(limit: int = 50) -> List[Dict[str, Any]]:
    result = (
        supabase.table("mistakes")
        .select("*")
        .eq("learner_id", LEARNER_ID)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def save_attempt(
    *,
    exercise_type: str,
    topic: str,
    stage: int,
    prompt_text: str,
    user_answer: str,
    score: int,
    correct: bool,
    explanation: str,
) -> None:
    supabase.table("exercise_attempts").insert(
        {
            "learner_id": LEARNER_ID,
            "exercise_type": exercise_type,
            "topic": topic,
            "stage": stage,
            "prompt_text": prompt_text,
            "user_answer": user_answer,
            "score": score,
            "correct": correct,
            "explanation": explanation,
            "created_at": utc_now_iso(),
        }
    ).execute()


def save_mistake(
    *,
    topic: str,
    mistake_text: str,
    correction: str,
    explanation: str,
) -> None:
    supabase.table("mistakes").insert(
        {
            "learner_id": LEARNER_ID,
            "topic": topic,
            "mistake_text": mistake_text,
            "correction": correction,
            "explanation": explanation,
            "reviewed": False,
            "created_at": utc_now_iso(),
        }
    ).execute()


def save_message(role: str, content: str) -> None:
    supabase.table("chat_messages").insert(
        {
            "learner_id": LEARNER_ID,
            "role": role,
            "content": content,
            "created_at": utc_now_iso(),
        }
    ).execute()


# -----------------------------
# Grammar syllabus + Study Hub storage
# (defined early: exercises target syllabus points and record results)
# -----------------------------
# Grammar points per CEFR level: (name, example, curriculum Grammar topic).
# Every point belongs to a topic, so Grammar exercises can target it and the
# Study Hub can tick it automatically.
GRAMMAR_SYLLABUS: Dict[str, List[Tuple[str, str, str]]] = {
    "A1": [
        ("Personal pronouns: ich, du, er, sie, es, wir, ihr, sie, Sie", "Ich heiße Anna. Wer bist du?", "sein and haben"),
        ("sein: ich bin, du bist, er ist …", "Ich bin müde. Wir sind in Berlin.", "sein and haben"),
        ("haben: ich habe, du hast, er hat …", "Hast du heute Zeit?", "sein and haben"),
        ("Regular verbs in the present (-e, -st, -t, -en)", "Ich wohne in Köln. Er arbeitet viel.", "present tense of regular verbs"),
        ("Verb in position 2", "Heute lerne ich Deutsch.", "present tense of regular verbs"),
        ("können and möchten", "Ich möchte einen Kaffee. Kannst du kommen?", "present tense of regular verbs"),
        ("W-questions (wer, was, wo, woher, wie, wann)", "Woher kommst du?", "W-questions and yes/no questions"),
        ("Yes/no questions (verb first)", "Kommst du heute?", "W-questions and yes/no questions"),
        ("Definite article: der, die, das", "der Tisch, die Lampe, das Buch", "articles der, die, das and ein"),
        ("Indefinite article: ein, eine", "Das ist ein Hund. Das ist eine Katze.", "articles der, die, das and ein"),
        ("Plural of nouns", "das Buch → die Bücher, die Frau → die Frauen", "plural of nouns"),
        ("Negation with nicht and kein", "Ich habe keine Zeit. Ich komme nicht.", "negation with nicht and kein"),
        ("Akkusativ: den, einen, keinen", "Ich habe einen Bruder.", "Akkusativ basics"),
        ("mein, dein (my, your)", "Das ist mein Bruder. Ist das dein Handy?", "Akkusativ basics"),
    ],
    "A2": [
        ("Verb in position 2 (Satzklammer)", "Morgen fahre ich nach Hamburg.", "word order"),
        ("deshalb, trotzdem, dann + verb in position 2", "Ich bin krank, deshalb bleibe ich zu Hause.", "word order"),
        ("Imperativ (du, ihr, Sie)", "Komm bitte schnell! Warten Sie hier.", "imperative"),
        ("Komparativ und Superlativ", "Berlin ist größer als Bonn. Am liebsten trinke ich Tee.", "word order"),
        ("und, aber, oder, denn", "Ich komme nicht, denn ich habe keine Zeit.", "main clause vs subordinate clause"),
        ("Nebensätze mit weil, dass, wenn", "Ich glaube, dass er heute kommt.", "main clause vs subordinate clause"),
        ("Indirekte Fragen mit ob und W-Wort", "Weißt du, wann der Zug kommt?", "main clause vs subordinate clause"),
        ("Akkusativ: Artikel und Pronomen", "Ich sehe den Mann. Ich sehe ihn.", "Akkusativ and Dativ"),
        ("Dativ: Artikel und Pronomen", "Ich gebe dem Kind ein Buch. Ich helfe ihm.", "Dativ basics"),
        ("Verben mit Dativ (helfen, gefallen, gehören)", "Die Jacke gefällt mir.", "Dativ basics"),
        ("Possessivartikel im Akkusativ und Dativ", "Ich rufe meinen Bruder an. Ich helfe meiner Mutter.", "possessive articles"),
        ("Reflexive Verben", "Ich freue mich auf das Wochenende.", "Akkusativ and Dativ"),
        ("Adjektivendungen (nach der/ein)", "Ich kaufe einen neuen Tisch.", "Akkusativ and Dativ"),
        ("Präpositionen mit Dativ (mit, bei, nach, von, zu, aus, seit)", "Ich fahre mit dem Bus zur Arbeit.", "prepositions of place and time"),
        ("Präpositionen mit Akkusativ (für, durch, gegen, ohne, um)", "Das Geschenk ist für meinen Vater.", "common prepositions"),
        ("Wechselpräpositionen: wo? (Dativ) / wohin? (Akkusativ)", "Ich bin im Park. Ich gehe in den Park.", "prepositions of place and time"),
        ("Zeitangaben (am, im, um, vor, seit)", "Seit zwei Jahren wohne ich hier.", "prepositions of place and time"),
        ("Modalverben (können, müssen, dürfen, sollen, wollen, möchten)", "Ich muss heute lange arbeiten.", "modal verbs"),
        ("Konjunktiv II: würde, hätte, wäre, könnte (höflich)", "Könnten Sie mir bitte helfen?", "modal verbs"),
        ("Trennbare Verben", "Ich rufe dich morgen an.", "separable verbs"),
        ("Perfekt mit haben und sein", "Wir sind nach Berlin gefahren.", "Perfekt with haben and sein"),
        ("Präteritum von sein, haben und Modalverben", "Ich war müde und musste schlafen.", "Perfekt and Präteritum basics"),
    ],
    "B1": [
        ("Nebensätze mit als und wenn (Vergangenheit)", "Als ich klein war, wohnte ich in Köln.", "dass, weil and wenn clauses"),
        ("Präteritum regelmäßiger und unregelmäßiger Verben", "Er kam spät und ging sofort ins Bett.", "Perfekt vs Präteritum in context"),
        ("Plusquamperfekt", "Nachdem ich gegessen hatte, ging ich los.", "Perfekt vs Präteritum in context"),
        ("Futur I", "Morgen wird es regnen.", "Perfekt vs Präteritum in context"),
        ("Wechselpräpositionen: stellen/stehen, legen/liegen, hängen", "Ich stelle die Flasche auf den Tisch.", "two-way prepositions"),
        ("Adjektivdeklination in allen Fällen", "Mit meinem alten Freund gehe ich ins neue Kino.", "adjective endings"),
        ("Genitiv und wegen, trotz, während", "Wegen des Regens bleiben wir zu Hause.", "adjective endings"),
        ("n-Deklination", "Ich frage meinen Kollegen.", "adjective endings"),
        ("Verben mit Präpositionen (warten auf, sich freuen über)", "Ich warte auf den Bus.", "verbs with prepositions"),
        ("da- und wo-Wörter (darauf, worauf)", "Worauf wartest du? Darauf, dass er kommt.", "verbs with prepositions"),
        ("Relativsätze (Nominativ, Akkusativ, Dativ)", "Das ist der Mann, dem ich geholfen habe.", "relative clauses"),
        ("Relativsätze mit Präposition", "Die Stadt, in der ich wohne, ist klein.", "relative clauses"),
        ("Konjunktiv II: Wünsche, Ratschläge, irreale Bedingungen", "Wenn ich Zeit hätte, würde ich reisen.", "Konjunktiv II"),
        ("Konjunktiv II Vergangenheit", "Ich hätte dich angerufen, wenn …", "Konjunktiv II"),
        ("Passiv Präsens und Präteritum", "Das Haus wurde 1990 gebaut.", "passive voice"),
        ("Passiv mit Modalverben", "Die Rechnung muss bezahlt werden.", "passive voice"),
        ("lassen + Infinitiv", "Ich lasse mein Auto reparieren.", "passive voice"),
        ("Komparativ und Superlativ als Attribut", "Das ist das schönste Zimmer im Hotel.", "comparatives"),
        ("Reflexive Verben mit Dativ", "Ich wasche mir die Hände.", "reflexive constructions"),
        ("obwohl, damit, um … zu, ohne … zu", "Ich lerne Deutsch, um in Berlin zu arbeiten.", "advanced conjunctions"),
        ("Zweiteilige Konnektoren (sowohl … als auch, weder … noch)", "Er spricht weder Englisch noch Französisch.", "advanced conjunctions"),
        ("Infinitiv mit zu", "Es ist schwer, früh aufzustehen.", "advanced conjunctions"),
        ("Indirekte Fragen", "Kannst du mir sagen, ob der Laden offen ist?", "indirect questions"),
    ],
    "B2": [
        ("Konnektoren: indem, sodass, je … desto", "Je mehr ich lese, desto besser verstehe ich.", "advanced connectors"),
        ("Konzessive Konnektoren (zwar … aber, dennoch)", "Das Hotel war zwar teuer, aber sehr schön.", "advanced connectors"),
        ("Textverweise (dies, derjenige, dabei)", "Dabei handelt es sich um …", "advanced connectors"),
        ("Nominalisierung", "Nach dem Ankommen → Nach der Ankunft", "nominalisation"),
        ("Konjunktiv I in der indirekten Rede", "Er sagte, er habe keine Zeit.", "Konjunktiv I for reported speech"),
        ("Partizipialattribute", "das von mir geschriebene Buch", "participle attributes"),
        ("Präpositionen mit Genitiv (aufgrund, bezüglich, innerhalb)", "Aufgrund des Streiks fällt der Zug aus.", "formal register"),
        ("Nomen-Verb-Verbindungen", "eine Entscheidung treffen, zur Verfügung stellen", "formal register"),
        ("Passiversatz (sich lassen, -bar, sein + zu)", "Das Problem lässt sich lösen.", "alternatives to the passive"),
        ("Zustandspassiv", "Die Tür ist geöffnet.", "alternatives to the passive"),
        ("Erweiterte Infinitive (statt … zu, ohne … zu)", "Statt zu lernen, sah er fern.", "complex sentence structure"),
        ("Relativsätze mit was, wo(r)- + Präposition", "Alles, was du sagst, stimmt.", "complex sentence structure"),
        ("Irreale Vergleiche (als ob)", "Er tut so, als ob er alles wüsste.", "complex sentence structure"),
        ("Modalverben mit subjektiver Bedeutung", "Er soll sehr reich sein.", "complex sentence structure"),
        ("Futur II und Vermutungen", "Sie wird den Zug verpasst haben.", "complex sentence structure"),
    ],
}
POINT_MASTER_SCORE = 85
POINT_MASTER_MIN = 3


def grammar_point_id(level: str, name: str) -> str:
    return f"{level}-{normalize_answer(name)}"


def grammar_points_for_topic(topic: str) -> List[Tuple[str, str, str]]:
    """(id, name, example) of every syllabus point practised under a Grammar topic."""
    key = normalize_answer(str(topic or ""))
    return [
        (grammar_point_id(level, name), name, example)
        for level, items in GRAMMAR_SYLLABUS.items()
        for name, example, t in items
        if normalize_answer(t) == key
    ]


def hub_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def hub_load() -> Dict[str, Any]:
    """Study Hub state (Supabase table `study_hub`), cached per browser session."""
    if "hub_state" in st.session_state:
        return st.session_state.hub_state
    state: Dict[str, Any] = {}
    db_ok = True
    try:
        res = (
            supabase.table("study_hub").select("data")
            .eq("learner_id", LEARNER_ID).limit(1).execute()
        )
        if res.data:
            state = res.data[0].get("data") or {}
    except Exception:
        db_ok = False
    start = hub_monday(date.today())
    state.setdefault("start_date", start.isoformat())
    state.setdefault("goal_label", "Goethe B1 exam")
    state.setdefault("goal_date", (start + timedelta(weeks=12)).isoformat())
    state.setdefault("done", [])
    state.setdefault("grammar_known", [])
    state.setdefault("grammar_scores", {})
    st.session_state.hub_state = state
    st.session_state.hub_db_ok = db_ok
    return state


def hub_save(state: Dict[str, Any]) -> None:
    # Always try: if the table was created during this session, this save
    # stores everything kept in the session so far.
    st.session_state.hub_state = state
    try:
        supabase.table("study_hub").upsert(
            {"learner_id": LEARNER_ID, "data": state, "updated_at": utc_now_iso()},
            on_conflict="learner_id",
        ).execute()
        st.session_state.hub_db_ok = True
    except Exception:
        st.session_state.hub_db_ok = False


def grammar_point_status(point_id: str) -> Tuple[str, int, Optional[int]]:
    """('mastered' | 'learning' | 'not_started', exercises, average of the last 5)."""
    scores = (hub_load().get("grammar_scores") or {}).get(point_id) or []
    if not scores:
        return "not_started", 0, None
    recent = scores[-5:]
    avg = round(sum(recent) / len(recent))
    if len(scores) >= POINT_MASTER_MIN and avg >= POINT_MASTER_SCORE:
        return "mastered", len(scores), avg
    return "learning", len(scores), avg


def pick_grammar_point(topic: str) -> Optional[Tuple[str, str, str]]:
    """The least-practised, not yet mastered syllabus point of a Grammar topic."""
    points = grammar_points_for_topic(topic)
    if not points:
        return None
    scores = hub_load().get("grammar_scores") or {}
    open_points = [p for p in points if grammar_point_status(p[0])[0] != "mastered"] or points
    return min(open_points, key=lambda p: len(scores.get(p[0]) or []))


def record_grammar_point(point_id: str, score: int) -> None:
    state = hub_load()
    all_scores = state.setdefault("grammar_scores", {})
    all_scores[point_id] = (all_scores.get(point_id) or [])[-9:] + [int(score)]
    hub_save(state)


# -----------------------------
# Level vocabulary: Gemini builds the word list, a quick check measures what you know
# -----------------------------
# Stored in the Supabase table `vocab`:
#   create table if not exists vocab (
#     learner_id text primary key,
#     data jsonb not null default '{}'::jsonb,
#     updated_at timestamptz default now()
#   );
# Without it, the list and results only last for the current browser session.
VOCAB_LEVEL_STAGES = {"A1": [1], "A2": [2, 3], "B1": [4, 5], "B2": [6, 7, 8]}
VOCAB_CHECK_SIZE = 10


def vocab_level_topics(level: str) -> List[str]:
    topics: List[str] = []
    for stage_number in VOCAB_LEVEL_STAGES[level]:
        for t in get_mode_topics(get_stage(stage_number), "Vocabulary"):
            if t not in topics:
                topics.append(t)
    return topics


def vocab_load() -> Dict[str, Any]:
    if "vocab_state" in st.session_state:
        return st.session_state.vocab_state
    state: Dict[str, Any] = {}
    db_ok = True
    try:
        res = supabase.table("vocab").select("data").eq("learner_id", LEARNER_ID).limit(1).execute()
        if res.data:
            state = res.data[0].get("data") or {}
    except Exception:
        db_ok = False
    state.setdefault("lists", {})
    state.setdefault("mem", {})
    st.session_state.vocab_state = state
    st.session_state.vocab_db_ok = db_ok
    return state


def vocab_save(state: Dict[str, Any]) -> None:
    # Always try: if the table was created during this session, this save
    # stores the whole word list and all results kept in the session so far.
    st.session_state.vocab_state = state
    try:
        supabase.table("vocab").upsert(
            {"learner_id": LEARNER_ID, "data": state, "updated_at": utc_now_iso()},
            on_conflict="learner_id",
        ).execute()
        st.session_state.vocab_db_ok = True
    except Exception:
        st.session_state.vocab_db_ok = False


def vocab_generate_topic(level: str, topic: str, existing: List[str]) -> List[Dict[str, str]]:
    """Ask Gemini for the essential words of one topic at one level."""
    system = f"""
You are building a German vocabulary list for a learner preparing for CEFR level {level}.

Topic: {topic}

List the essential words a learner must know for this topic at level {level}
(including the basic words from lower levels). YOU decide how many are essential at
this level, typically between 30 and 70. Prefer high-frequency, practical words.
Do not include any of these words again: {json.dumps(existing[-150:], ensure_ascii=False)}

Rules for each word:
- `de`: nouns ALWAYS with der/die/das and a capital letter ("der Termin");
  verbs in the infinitive ("einkaufen", "sich beeilen"); max 3 words, no punctuation.
- `en`: short English meaning (1–4 words).
- `emoji`: one emoji that pictures it.
- `ex`: one short German example sentence at level {level}.

Return ONLY valid JSON: {{"words": [{{"de": "...", "en": "...", "emoji": "...", "ex": "..."}}]}}
"""
    raw = call_llm(
        [{"role": "system", "content": system},
         {"role": "user", "content": "Create the word list now."}],
        temperature=0.3,
    )
    data = parse_json_from_model(raw) or {}
    seen = {normalize_answer(x) for x in existing}
    words = []
    for w in data.get("words") or []:
        if not isinstance(w, dict):
            continue
        de = " ".join(str(w.get("de") or "").split())
        en = str(w.get("en") or "").strip()
        if not de or not en or len(de) > 40 or normalize_answer(de) in seen:
            continue
        first = de.split(" ")[0]
        if first[:1].isupper() and first.lower() not in ("der", "die", "das") and " " not in de:
            continue  # a noun without its article would teach the wrong answer
        seen.add(normalize_answer(de))
        words.append({"de": de, "en": en, "emoji": str(w.get("emoji") or "").strip(),
                      "ex": str(w.get("ex") or "").strip()[:160], "topic": topic})
    return words


def vocab_norm(text: str) -> str:
    text = str(text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    text = re.sub(r"[.,!?;:\"']", "", text)
    return re.sub(r"\s+", " ", text).strip()


def vocab_check_answer(typed: str, target: str) -> str:
    """'correct', 'article' (right noun, wrong der/die/das), 'close' (small typo) or 'wrong'."""
    t, g = vocab_norm(typed), vocab_norm(target)
    if t == g:
        return "correct"
    tp, gp = t.split(" ", 1), g.split(" ", 1)
    arts = ("der", "die", "das")
    if len(tp) == 2 and len(gp) == 2 and tp[0] in arts and gp[0] in arts and tp[1] == gp[1]:
        return "article"
    # Small typo check (one edit away).
    if abs(len(t) - len(g)) <= 1 and sum(1 for a, b in zip(t, g) if a != b) + abs(len(t) - len(g)) <= 1:
        return "close"
    return "wrong"


def vocab_status(m: Optional[Dict[str, Any]]) -> str:
    """'known': right on the first try ever, or right on 2+ different days (last answer right).
    'learning': seen but not known yet. 'new': never asked."""
    if not m:
        return "new"
    if m.get("first_ok") and m.get("last_ok"):
        return "known"
    if len(set(m.get("ok_days") or [])) >= 2 and m.get("last_ok"):
        return "known"
    return "learning"


def vocab_record(state: Dict[str, Any], de: str, ok: bool) -> None:
    mem = state.setdefault("mem", {})
    m = mem.get(de)
    today = date.today().isoformat()
    if m is None:
        m = {"first_ok": ok, "ok_days": [], "right": 0, "wrong": 0}
    m["right" if ok else "wrong"] = safe_int(m.get("right" if ok else "wrong")) + 1
    if ok and today not in m["ok_days"]:
        m["ok_days"] = (m["ok_days"] + [today])[-10:]
    m["last_ok"] = ok
    m["last"] = utc_now_iso()
    mem[de] = m


def vocab_pick_check(words: List[Dict[str, str]], mem: Dict[str, Any], n: int) -> List[Dict[str, str]]:
    """Learning words (last answer wrong first), then new words in list order, then old known ones."""
    learning = [w for w in words if vocab_status(mem.get(w["de"])) == "learning"]
    learning.sort(key=lambda w: (bool(mem[w["de"]].get("last_ok")), mem[w["de"]].get("last", "")))
    new = [w for w in words if vocab_status(mem.get(w["de"])) == "new"]
    known = sorted((w for w in words if vocab_status(mem.get(w["de"])) == "known"),
                   key=lambda w: mem[w["de"]].get("last", ""))
    # Mostly new words so the count grows; a few learning words for repetition.
    picked = learning[:4]
    picked += new[: n - len(picked)]
    picked += learning[4: 4 + n - len(picked)]
    picked += known[: n - len(picked)]
    return picked[:n]


def add_study_minutes(minutes: int) -> Dict[str, Any]:
    minutes = max(0, min(minutes, 600))
    progress = load_progress()

    total = safe_int(progress.get("total_study_minutes")) + minutes
    today = datetime.now().date().isoformat()
    last = progress.get("last_study_date")

    streak = safe_int(progress.get("current_streak"))
    longest = safe_int(progress.get("longest_streak"))

    if last == today:
        pass
    elif last:
        try:
            last_date = datetime.fromisoformat(last).date()
            day_delta = (datetime.now().date() - last_date).days
            if day_delta == 1:
                streak += 1
            else:
                streak = 1
        except ValueError:
            streak = 1
    else:
        streak = 1

    longest = max(longest, streak)

    progress["total_study_minutes"] = total
    progress["current_streak"] = streak
    progress["longest_streak"] = longest
    progress["last_study_date"] = today
    save_progress(progress)
    return progress


def compute_skill_score(
    attempts: List[Dict[str, Any]],
    exercise_type: str,
) -> Optional[int]:
    scores = [
        safe_int(a.get("score"))
        for a in attempts
        if a.get("exercise_type") == exercise_type
    ]
    if not scores:
        return None
    # Weight recent attempts more heavily.
    scores = scores[:20]
    weights = list(range(len(scores), 0, -1))
    weighted = sum(s * w for s, w in zip(scores, weights))
    return pct(weighted / sum(weights))


# -----------------------------
# Passing rule: a percentage you choose, or the Goethe-Zertifikat standard
# -----------------------------
# Goethe-Zertifikat: pass = 60% or more in each exam module (Lesen, Hören,
# Schreiben, Sprechen). Grammar/vocabulary exercises still count as practice.
GOETHE_MODULES = {"Reading": "Lesen", "Listening": "Hören", "Writing": "Schreiben", "Speaking": "Sprechen"}
GOETHE_PASS = 60
GOETHE_MIN_PER_MODULE = 3
PERCENT_CHOICES = [60, 65, 70, 75, 80, 85, 90]
PASS_MODE_LABELS = {
    "percentage": "Percentage (you choose the pass mark)",
    "goethe": "Goethe exam standard (60% in each exam skill)",
}


def pass_rule() -> Tuple[str, int]:
    """('percentage' | 'goethe', percent). Stored in the Study Hub state."""
    rule = hub_load().get("pass_rule") or {}
    mode = rule.get("mode") if rule.get("mode") in PASS_MODE_LABELS else "percentage"
    percent = safe_int(rule.get("percent"), 85)
    return mode, (percent if percent in PERCENT_CHOICES else 85)


def pass_mark() -> int:
    mode, percent = pass_rule()
    return GOETHE_PASS if mode == "goethe" else percent


def pass_rule_text() -> str:
    mode, percent = pass_rule()
    if mode == "goethe":
        return (f"Goethe standard: {GOETHE_PASS}%+ in each of Lesen, Hören, Schreiben and Sprechen "
                f"({GOETHE_MIN_PER_MODULE}+ exercises each)")
    return f"8+ exercises with an average of {percent}%+"


def goethe_module_scores(stage_attempts: List[Dict[str, Any]]) -> Dict[str, Tuple[int, Optional[int]]]:
    """skill -> (exercises in this stage, average of the last 5)."""
    out: Dict[str, Tuple[int, Optional[int]]] = {}
    for skill in GOETHE_MODULES:
        scores = [safe_int(a.get("score")) for a in stage_attempts if a.get("exercise_type") == skill]
        recent = scores[:5]  # newest first
        out[skill] = (len(scores), round(sum(recent) / len(recent)) if recent else None)
    return out


def goethe_ready(stage_attempts: List[Dict[str, Any]]) -> bool:
    return all(n >= GOETHE_MIN_PER_MODULE and avg is not None and avg >= GOETHE_PASS
               for n, avg in goethe_module_scores(stage_attempts).values())


def assess_stage_readiness(
    stage_attempts: List[Dict[str, Any]],
) -> Tuple[int, str]:
    """
    Decide whether the learner should stay, review, promote, or downgrade.

    Thresholds follow the chosen pass mark P: an answer below P counts as
    incorrect, below P-25 as a hard fail, below P-15 as weak. (With the
    default P = 85 these are 60 and 70, as before.)
    Downgrade is deliberately based on BOTH score and the saved `correct`
    flag. This makes the system robust when the grader gives a partial score
    to an answer that is still considered incorrect.
    """
    if not stage_attempts:
        return 0, "No evidence yet."

    recent = stage_attempts[:8]
    scores = [safe_int(a.get("score")) for a in recent]
    if not scores:
        return 0, "No scored attempts yet."

    mode, _ = pass_rule()
    p = pass_mark()
    low, weak = p - 25, p - 15

    recent_avg = round(sum(scores) / len(scores))
    incorrect_count = sum(
        1
        for a in recent
        if not bool(a.get("correct")) or safe_int(a.get("score")) < p
    )
    hard_fail_count = sum(
        1
        for a in recent
        if not bool(a.get("correct")) or safe_int(a.get("score")) < low
    )

    consecutive_low = 0
    for score in scores:
        if score < low:
            consecutive_low += 1
        else:
            break

    consecutive_weak = 0
    for score in scores:
        if score < weak:
            consecutive_weak += 1
        else:
            break

    # Fewer than 8 attempts: do not downgrade yet.
    if len(stage_attempts) < 8:
        if len(recent) >= 4 and (recent_avg < low or hard_fail_count >= 3):
            return recent_avg, "At risk — collect more evidence before downgrade."
        return recent_avg, "Continue current stage."

    # 8+ attempts: persistent weakness can now trigger a downgrade.
    if (
        incorrect_count >= 6
        or recent_avg < low
        or (recent_avg < weak and consecutive_low >= 3)
    ):
        return recent_avg, "Downgrade recommended."

    # Borderline performance: keep the stage but force more review.
    if recent_avg < weak or incorrect_count >= 4 or consecutive_weak >= 4:
        return recent_avg, "Needs intensive review."

    if mode == "goethe":
        if goethe_ready(stage_attempts):
            return recent_avg, "Ready for promotion."
    elif recent_avg >= p and incorrect_count <= 1:
        return recent_avg, "Ready for promotion."

    return recent_avg, "Continue current stage."


def refresh_derived_progress() -> Dict[str, Any]:
    progress = load_progress()
    attempts = get_recent_attempts(100)
    mistakes = get_recent_mistakes(100)

    current_stage = safe_int(progress.get("current_stage"), 1)
    current_stage = max(1, min(current_stage, len(CURRICULUM)))

    stage_attempts = [
        a for a in attempts if safe_int(a.get("stage")) == current_stage
    ]
    stage_scores = [safe_int(a.get("score")) for a in stage_attempts]

    stage_mastery = pct(
        sum(stage_scores) / len(stage_scores)
        if stage_scores
        else 0
    )

    lifetime_scores = [safe_int(a.get("score")) for a in attempts]
    overall_mastery = pct(
        sum(lifetime_scores) / len(lifetime_scores)
        if lifetime_scores
        else 0
    )

    total_attempts = len(attempts)
    total_correct = sum(1 for a in attempts if a.get("correct"))

    weak_topic_counts: Dict[str, int] = {}
    for m in mistakes:
        topic = (m.get("topic") or "General").strip()
        weak_topic_counts[topic] = weak_topic_counts.get(topic, 0) + 1

    weak_areas = [
        topic
        for topic, _ in sorted(
            weak_topic_counts.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )[:5]
    ]

    readiness_score, readiness_state = assess_stage_readiness(stage_attempts)

    # --------------------------------------------------------
    # AUTOMATIC DOWNGRADE
    # --------------------------------------------------------
    #
    # One mistake -> NO downgrade.
    # Several poor attempts -> warning/review.
    # Persistent poor performance -> downgrade by one stage.
    #
    if (
        current_stage > 1
        and readiness_state.strip().lower() == "downgrade recommended."
        and len(stage_attempts) >= 8
    ):
        current_stage -= 1
        progress["current_stage"] = current_stage
        progress["stage_mastery"] = 0
        progress["status"] = "Downgraded — Review Required"
        progress["overall_mastery"] = overall_mastery
        progress["lifetime_attempts"] = total_attempts
        progress["lifetime_correct"] = total_correct
        progress["weak_areas"] = weak_areas

        save_progress(progress)
        st.session_state["downgrade_message"] = (
            f"⚠️ Your recent performance ({readiness_score}%) is below the "
            f"required level for the previous stage. You have been moved back "
            f"to Stage {current_stage}: {get_stage(current_stage)['title']}. "
            f"This is a review stage — rebuild mastery here before advancing again."
        )
        return progress

    # --------------------------------------------------------
    # NORMAL STATUS
    # --------------------------------------------------------
    if readiness_state == "Ready for promotion.":
        status = "Ready to Advance"
    elif readiness_state == "Needs intensive review.":
        status = "Needs Intensive Review"
    elif readiness_state == "At risk — collect more evidence before downgrade.":
        status = "At Risk"
    elif readiness_state == "Downgrade recommended.":
        status = "At Risk"
    else:
        status = "On Track"

    progress["current_stage"] = current_stage
    progress["stage_mastery"] = stage_mastery
    progress["overall_mastery"] = overall_mastery
    progress["lifetime_attempts"] = total_attempts
    progress["lifetime_correct"] = total_correct
    progress["weak_areas"] = weak_areas
    progress["status"] = status

    save_progress(progress)
    return progress


def can_advance_stage(progress: Dict[str, Any]) -> bool:
    attempts = get_recent_attempts(100)
    stage = safe_int(progress.get("current_stage"), 1)
    stage_attempts = [a for a in attempts if safe_int(a.get("stage")) == stage]

    mode, percent = pass_rule()
    if mode == "goethe":
        # Like the Goethe-Zertifikat: every exam skill must pass on its own.
        return goethe_ready(stage_attempts)

    # Only structured exercise attempts can unlock a promotion.
    if len(stage_attempts) < 8:
        return False

    scores = [safe_int(a.get("score")) for a in stage_attempts[:20]]
    mastery = pct(sum(scores) / len(scores)) if scores else 0

    return mastery >= percent


def advance_stage_if_ready() -> Tuple[Dict[str, Any], bool, str]:
    progress = refresh_derived_progress()
    current_stage = safe_int(progress.get("current_stage"), 1)

    if current_stage >= len(CURRICULUM):
        return progress, False, "You have reached the final B2 stage."

    if not can_advance_stage(progress):
        return progress, False, ""

    new_stage = current_stage + 1
    progress["current_stage"] = new_stage
    progress["stage_mastery"] = 0
    progress["status"] = "New Stage Unlocked"
    save_progress(progress)

    stage = get_stage(new_stage)
    message = (
        f"🎉 **Stage {new_stage} unlocked:** {stage['level']} — "
        f"{stage['title']}. Your next lesson will automatically use the new stage."
    )
    return progress, True, message


def get_promotion_evidence(stage_no: int) -> Tuple[int, int]:
    """Return (exercises counted, average score) toward promotion for a stage."""
    attempts = get_recent_attempts(100)
    scores = [
        safe_int(a.get("score"))
        for a in attempts
        if safe_int(a.get("stage")) == stage_no
    ][:20]
    avg = pct(sum(scores) / len(scores)) if scores else 0
    return len(scores), avg


def reset_lesson_state() -> None:
    st.session_state.lesson_concept = None
    st.session_state.lesson_mode = None
    st.session_state.lesson_mode_choice = None
    st.session_state.current_exercise = None
    st.session_state.last_result = None


def set_stage_manually(new_stage: int) -> None:
    """Let the learner choose their own level (e.g. after a placement test).

    The normal promotion/downgrade rules keep running from the chosen stage,
    using the learner's passing rule (percentage or Goethe standard).
    """
    new_stage = max(1, min(new_stage, len(CURRICULUM)))
    progress = load_progress()
    old_stage = safe_int(progress.get("current_stage"), 1)

    progress["current_stage"] = new_stage
    progress["stage_mastery"] = 0
    progress["status"] = "Self-selected Level"
    save_progress(progress)

    stage = get_stage(new_stage)
    save_message(
        "system",
        f"LEVEL CHANGED MANUALLY: Stage {old_stage} -> Stage {new_stage} "
        f"({stage['level']} — {stage['title']}). Learner selected this level.",
    )

    # Start a clean learning context for the new level.
    reset_lesson_state()
    st.session_state.taught_concept_topics = []

    st.session_state["unlock_message"] = (
        f"🎚️ Level set to **Stage {new_stage}: {stage['level']} — {stage['title']}**. "
        f"You move up automatically once you reach your passing rule: {pass_rule_text()}."
    )


# -----------------------------
# Audio
# -----------------------------
def german_audio(text: str) -> None:
    try:
        fp = io.BytesIO()
        tts = gTTS(text=text, lang="de", slow=False)
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3")
    except Exception as exc:
        st.caption(f"Audio unavailable: {exc}")


# -----------------------------
# AI exercise generation
# -----------------------------
def stage_topic_is_valid(topic: str, stage: Dict[str, Any]) -> bool:
    """Return True only when the topic belongs to the current stage (any skill)."""
    topic_norm = normalize_answer(str(topic or ""))
    allowed = [normalize_answer(str(t)) for t in all_stage_topics(stage)]
    return bool(topic_norm) and topic_norm in allowed


def exercise_matches_stage(exercise: Dict[str, Any], stage: Dict[str, Any]) -> bool:
    """Strict guard: generated content must identify a current-stage topic."""
    return stage_topic_is_valid(exercise.get("topic", ""), stage)


def pick_least_practiced(topics: List[str], recent_attempts: List[Dict[str, Any]]) -> str:
    recent_topics = [normalize_answer(str(a.get("topic", ""))) for a in recent_attempts]
    return min(topics, key=lambda t: recent_topics.count(normalize_answer(t)))


def generate_lesson_concept(
    progress: Dict[str, Any],
    mode: str,
    previous_concept: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a genuinely new lesson concept for the selected skill.

    The topic pool comes from the current stage AND the selected skill, so
    Vocabulary/Listening/etc. never turn into grammar lessons. Weak areas can
    only rank topics inside that pool.
    """
    stage_no = safe_int(progress.get("current_stage"), 1)
    stage = get_stage(stage_no)
    pool = get_mode_topics(stage, mode)

    recent_attempts = get_recent_attempts(30)
    recent_topic_counts = {
        topic: sum(
            1 for a in recent_attempts
            if normalize_answer(str(a.get("topic") or "")) == normalize_answer(topic)
        )
        for topic in pool
    }

    weak_areas = progress.get("weak_areas") or []
    weak_norm = {normalize_answer(str(x)) for x in weak_areas}

    # Concepts taught during this Streamlit session are excluded even if no
    # exercise has been submitted yet (therefore they are not in the DB).
    taught_topics = st.session_state.setdefault("taught_concept_topics", [])
    taught_norm = {normalize_answer(str(x)) for x in taught_topics}

    previous_topic = normalize_answer(str((previous_concept or {}).get("topic") or ""))
    previous_title = normalize_answer(str((previous_concept or {}).get("title") or ""))

    fresh_pool = [
        t for t in pool
        if normalize_answer(t) not in taught_norm
        and normalize_answer(t) != previous_topic
    ]

    # If every topic in the skill has already been taught this session, allow
    # repeats rather than becoming stuck forever.
    candidate_pool = fresh_pool or [
        t for t in pool if normalize_answer(t) != previous_topic
    ] or pool

    weak_candidates = [t for t in candidate_pool if normalize_answer(t) in weak_norm]
    target_topic = min(
        weak_candidates or candidate_pool,
        key=lambda t: recent_topic_counts.get(t, 0),
    )

    recent_summary = [
        {"type": a.get("exercise_type"), "topic": a.get("topic"), "score": a.get("score")}
        for a in recent_attempts[:12]
    ]

    teaching_style = MODE_TEACHING_STYLE.get(mode, MODE_TEACHING_STYLE["Grammar"])

    for _ in range(3):
        system = f"""
You are an excellent German teacher.

CURRENT LEARNER STAGE — ABSOLUTE HARD BOUNDARY:
Stage {stage_no}: {stage["level"]} — {stage["title"]}
Use language appropriate for level {stage["level"]}. Do not go above it.
{language_rules(stage_no)}

SKILL / MODE: {mode}
HOW TO TEACH THIS SKILL — MANDATORY:
{teaching_style}

TARGET CONCEPT — MANDATORY:
{target_topic}

The lesson MUST teach exactly the TARGET CONCEPT through the {mode} skill.
The JSON topic field MUST be exactly: {target_topic}

CONCEPTS ALREADY TAUGHT IN THIS SESSION — DO NOT REPEAT:
{json.dumps(taught_topics, ensure_ascii=False)}

PREVIOUS LESSON — DO NOT REPEAT:
{json.dumps({"topic": (previous_concept or {}).get("topic"), "title": (previous_concept or {}).get("title")}, ensure_ascii=False)}

RECENT EXERCISE HISTORY — REVIEW CONTEXT ONLY:
{json.dumps(recent_summary, ensure_ascii=False)}

FORMAT RULES:
- `rules` is a list of short plain-text strings, one point per item.
  No markdown, no nested lists, no line breaks inside an item.
- `sample_text` is German text only (empty string if not needed).

Return ONLY valid JSON:
{{
  "topic": "{target_topic}",
  "title": "...",
  "explanation": "...",
  "rules": ["..."],
  "examples": [{{"german": "...", "english": "...", "note": "..."}}],
  "sample_text": "...",
  "common_mistakes": ["..."],
  "quick_check": "...",
  "target_skill": "{mode}"
}}
"""
        raw = call_llm(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": "Teach me this new concept now."},
            ],
            temperature=0.45,
        )
        concept = parse_json_from_model(raw)
        if not concept:
            continue

        returned_topic = normalize_answer(str(concept.get("topic") or ""))
        returned_title = normalize_answer(str(concept.get("title") or ""))
        if returned_topic != normalize_answer(target_topic):
            continue
        if previous_title and returned_title == previous_title:
            continue

        concept["topic"] = target_topic
        concept["title"] = concept.get("title") or target_topic
        concept["explanation"] = concept.get("explanation") or f"Today: {target_topic}."
        concept["rules"] = concept.get("rules") or []
        concept["examples"] = concept.get("examples") or []
        concept["sample_text"] = concept.get("sample_text") or ""
        concept["common_mistakes"] = concept.get("common_mistakes") or []
        concept["quick_check"] = concept.get("quick_check") or ""
        concept["target_skill"] = mode
        concept["stage"] = stage_no

        if target_topic not in taught_topics:
            taught_topics.append(target_topic)
        # Keep session memory compact.
        if len(taught_topics) > 20:
            del taught_topics[:-20]
        return concept

    raise ValueError(
        f"The lesson generator could not produce the required new topic '{target_topic}'."
    )


EXERCISE_MODE_RULES = """
For exercise modes:
- Grammar: one focused grammar task.
- Vocabulary: practical German vocabulary in context (e.g. fill in the right
  word, give article + plural, match words to meanings). NOT a grammar drill.
- Listening: put a short German text (dialogue/announcement) in `transcript`
  for TTS audio, and ask comprehension questions about it in `question`.
  Do NOT show the transcript inside the question.
- Reading: short authentic-style German text + comprehension question, both
  inside `question`.
- Writing: realistic German writing task (email, message, short text).
- Speaking: realistic speaking prompt the learner answers in German.
"""


def generate_exercise(
    progress: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    stage_no = safe_int(progress.get("current_stage"), 1)
    stage = get_stage(stage_no)
    weak_areas = progress.get("weak_areas") or []
    recent = get_recent_attempts(12)
    persistent_history = load_legacy_history_for_context(8)
    recently_completed = get_recent_exercise_prompts(20)

    mode_topics = get_mode_topics(stage, mode)

    active_concept = st.session_state.get("lesson_concept") or {}
    active_topic = str(active_concept.get("topic") or "").strip()
    if active_topic and stage_topic_is_valid(active_topic, stage):
        target_topic = active_topic
    else:
        target_topic = pick_least_practiced(mode_topics, recent)

    # Grammar exercises aim at one syllabus point (the least practised one),
    # so the Study Hub can tick grammar points automatically.
    grammar_point = pick_grammar_point(target_topic) if mode == "Grammar" else None
    point_rule = (
        f"GRAMMAR POINT TO TEST — MANDATORY: {grammar_point[1]} "
        f"(example: „{grammar_point[2]}“)\n"
        if grammar_point else ""
    )

    recent_summary = [
        {
            "type": a.get("exercise_type"),
            "topic": a.get("topic"),
            "score": a.get("score"),
        }
        for a in recent
    ]

    system = f"""
You are a rigorous German teacher helping an adult learner progress toward
professional B2.

CURRENT STAGE — HARD BOUNDARY:
Stage {stage_no}: {stage["level"]} — {stage["title"]}
Use language appropriate for level {stage["level"]}.
{language_rules(stage_no)}
Allowed topics for {mode} ONLY: {", ".join(mode_topics)}
TARGET TOPIC FOR THIS EXERCISE: {target_topic}
{point_rule}
MODE: {mode}
The exercise MUST be a genuine {mode} exercise.

WEAK AREAS (review only; NEVER use these to change the stage or the mode):
{", ".join(weak_areas) if weak_areas else "No established weak area yet"}

RECENT PERFORMANCE:
{json.dumps(recent_summary, ensure_ascii=False)}

RECENT LEARNER/COACH HISTORY:
{json.dumps(persistent_history, ensure_ascii=False)}

RECENTLY COMPLETED EXERCISES — DO NOT REPEAT:
{json.dumps(recently_completed, ensure_ascii=False)}

ACTIVE LESSON CONCEPT:
{json.dumps(active_concept, ensure_ascii=False)}

If an active lesson concept exists, the exercise MUST directly practice that concept.
The learner has just been taught it, so make the first exercise guided and accessible.

Create ONE NEW exercise that is challenging but appropriate for the current stage.
The `topic` field MUST be copied exactly from the TARGET TOPIC.
Do not jump to a higher CEFR level.

IMPORTANT NOVELTY RULE:
The exercise must not repeat a recently completed exercise. Use a fresh
sentence, context, names, numbers, vocabulary combination, or scenario.
{EXERCISE_MODE_RULES}
Return ONLY valid JSON:
{{
  "mode": "{mode}",
  "topic": "{target_topic}",
  "question": "...",
  "expected_answer": "...",
  "accepted_answers": ["..."],
  "transcript": "...",
  "scoring_rubric": "...",
  "target_skill": "{mode}"
}}

For open-ended writing/speaking tasks, expected_answer may be an empty string.
"""

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": "Generate the next exercise now."},
        ],
        temperature=0.6,
    )

    exercise = parse_json_from_model(raw)
    if not exercise:
        raise ValueError("The AI did not return valid exercise JSON.")

    exercise["topic"] = exercise.get("topic") or target_topic
    exercise["question"] = exercise.get("question") or "Bitte beantworte die Aufgabe."
    exercise["accepted_answers"] = exercise.get("accepted_answers") or []
    exercise["transcript"] = exercise.get("transcript") or ""
    exercise["expected_answer"] = exercise.get("expected_answer") or ""
    exercise["target_skill"] = mode

    # Never allow the model to silently switch away from the lesson being practiced.
    if active_topic and stage_topic_is_valid(active_topic, stage):
        exercise["topic"] = active_topic

    exercise["mode"] = mode
    exercise["grammar_point"] = grammar_point[0] if grammar_point else ""
    return exercise


def grade_answer(
    exercise: Dict[str, Any],
    user_answer: str,
) -> Dict[str, Any]:
    mode = exercise.get("mode", "Grammar")
    topic = exercise.get("topic", "General")
    expected = exercise.get("expected_answer", "")
    accepted = exercise.get("accepted_answers", [])

    # For Grammar, ask which syllabus point the exercise tested (numbered list).
    points = grammar_points_for_topic(topic) if mode == "Grammar" else []
    point_rule = ""
    if points:
        listing = "\n".join(f"   {i}. {name}" for i, (_, name, _) in enumerate(points, 1))
        point_rule = (
            "6b. `grammar_point`: the number of the grammar point this exercise mainly tests,\n"
            f"   or 0 if none fits:\n{listing}\n"
        )

    system = f"""
You are grading a German learner's answer.
{language_rules(safe_int(exercise.get('stage'), 1))} This applies to `explanation`; `corrected_answer` and `improved_version` stay in German.

Mode: {mode}
Topic: {topic}
Question:
{exercise.get("question", "")}

Listening transcript (if any):
{exercise.get("transcript", "")}

Expected answer:
{expected}

Accepted answers:
{json.dumps(accepted, ensure_ascii=False)}

Learner answer:
{user_answer}

Rules:
1. Score from 0 to 100.
2. Be strict about the targeted German skill ({mode}).
3. Do not penalize harmless punctuation differences.
4. For open-ended answers, judge grammar, vocabulary, correctness,
   task completion, and naturalness.
5. For a correct answer with a minor stylistic alternative, do not mark it wrong.
6. Identify the MAIN error topic if there is one.
{point_rule}7. Return ONLY valid JSON:

{{
  "score": 0,
  "correct": false,
  "corrected_answer": "...",
  "explanation": "...",
  "main_error_topic": "...",
  "error_text": "...",
  "improved_version": "...",
  "grammar_point": 0
}}
"""

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": "Grade the learner answer."},
        ],
        temperature=0.1,
    )

    result = parse_json_from_model(raw)
    if not result:
        # Safe fallback: do not invent a high score.
        return {
            "score": 0,
            "correct": False,
            "corrected_answer": "",
            "explanation": "Automatic grading failed. Please retry.",
            "main_error_topic": topic,
            "error_text": user_answer,
            "improved_version": "",
        }

    result["score"] = max(0, min(100, safe_int(result.get("score"))))

    raw_correct = result.get("correct")
    if isinstance(raw_correct, bool):
        model_correct = raw_correct
    elif isinstance(raw_correct, str):
        model_correct = raw_correct.strip().lower() in {
            "true", "yes", "correct", "1"
        }
    elif isinstance(raw_correct, (int, float)):
        model_correct = bool(raw_correct)
    else:
        model_correct = False

    # A score at or above the pass mark counts as correct even if the model omitted the flag.
    result["correct"] = model_correct or result["score"] >= pass_mark()

    # Which syllabus point this exercise counts for: the grader's pick, else
    # the point the exercise was generated for.
    point_no = safe_int(result.get("grammar_point"))
    result["grammar_point"] = (
        points[point_no - 1][0] if 1 <= point_no <= len(points)
        else exercise.get("grammar_point") or ""
    )
    return result


# -----------------------------
# Exercise de-duplication
# -----------------------------
def get_recent_exercise_prompts(limit: int = 20) -> List[str]:
    """Recently used prompts, so the AI can avoid repeating an exercise."""
    try:
        result = (
            supabase.table("exercise_attempts")
            .select("prompt_text")
            .eq("learner_id", LEARNER_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [
            str(row.get("prompt_text", "")).strip()
            for row in (result.data or [])
            if row.get("prompt_text")
        ]
    except Exception:
        return []


def is_duplicate_exercise(
    exercise: Dict[str, Any],
    recent_prompts: List[str],
) -> bool:
    """Detect exact or near-exact repeats."""
    question = normalize_answer(str(exercise.get("question", "")))
    if not question:
        return True

    q_tokens = set(re.findall(r"\b[\wäöüß]+\b", question))
    for old_prompt in recent_prompts:
        old = normalize_answer(old_prompt)

        if question == old:
            return True

        # Catch cases where the model only changes a few words.
        o_tokens = set(re.findall(r"\b[\wäöüß]+\b", old))
        if len(q_tokens) >= 8 and len(o_tokens) >= 8:
            overlap = len(q_tokens & o_tokens) / max(
                1, min(len(q_tokens), len(o_tokens))
            )
            if overlap >= 0.82:
                return True

    return False


def generate_unique_exercise(
    progress: Dict[str, Any],
    mode: str,
    max_attempts: int = 5,
) -> Dict[str, Any]:
    """Generate an exercise that is inside the stage and not a recent repeat."""
    recent_prompts = get_recent_exercise_prompts(20)
    exercise: Optional[Dict[str, Any]] = None
    fresh_stage_no = safe_int(progress.get("current_stage"), 1)

    for _ in range(max_attempts):
        # Re-read progress so a downgrade/promotion is honored immediately.
        fresh_progress = refresh_derived_progress()
        fresh_stage_no = safe_int(fresh_progress.get("current_stage"), 1)
        fresh_stage = get_stage(fresh_stage_no)

        exercise = generate_exercise(fresh_progress, mode)

        if not exercise_matches_stage(exercise, fresh_stage):
            exercise = None
        elif not is_duplicate_exercise(exercise, recent_prompts):
            exercise["stage"] = fresh_stage_no
            return exercise

        # The model drifted outside the stage or repeated an exercise:
        # use a stricter, novelty-focused regeneration prompt.
        mode_topics = get_mode_topics(fresh_stage, mode)
        active_concept = st.session_state.get("lesson_concept") or {}
        active_topic = str(active_concept.get("topic") or "").strip()
        if active_topic and stage_topic_is_valid(active_topic, fresh_stage):
            target_topic = active_topic
        else:
            target_topic = pick_least_practiced(mode_topics, get_recent_attempts(12))

        novelty_system = f"""
You are generating the next German exercise.

CURRENT STAGE — HARD BOUNDARY:
Stage {fresh_stage_no}: {fresh_stage["level"]} — {fresh_stage["title"]}
Allowed topics for {mode} ONLY: {", ".join(mode_topics)}
TARGET TOPIC: {target_topic}

MODE: {mode} — the exercise MUST be a genuine {mode} exercise.

DO NOT REPEAT any of these recently completed questions:
{json.dumps(recent_prompts[:10], ensure_ascii=False)}

Create a completely NEW exercise:
- different sentence/context
- different names/numbers/examples
- different wording
- same CEFR level as Stage {fresh_stage_no} ({fresh_stage["level"]})
- {language_rules(fresh_stage_no)}
- `topic` MUST be exactly `{target_topic}`
{EXERCISE_MODE_RULES}
Return ONLY valid JSON with:
mode, topic, question, expected_answer, accepted_answers,
transcript, scoring_rubric, target_skill.
"""

        raw = call_llm(
            [
                {"role": "system", "content": novelty_system},
                {
                    "role": "user",
                    "content": (
                        "Generate a different exercise now. "
                        "Do not reuse any previous question."
                    ),
                },
            ],
            temperature=0.85,
        )

        regenerated = parse_json_from_model(raw)
        if regenerated:
            regenerated["mode"] = mode
            regenerated["topic"] = regenerated.get("topic") or target_topic
            regenerated["question"] = regenerated.get("question") or ""
            regenerated["accepted_answers"] = regenerated.get("accepted_answers") or []
            regenerated["transcript"] = regenerated.get("transcript") or ""
            regenerated["expected_answer"] = regenerated.get("expected_answer") or ""
            regenerated["target_skill"] = mode

            if (
                exercise_matches_stage(regenerated, fresh_stage)
                and not is_duplicate_exercise(regenerated, recent_prompts)
            ):
                regenerated["stage"] = fresh_stage_no
                return regenerated

    # Last resort: accept a stage-valid exercise even if it resembles an old one.
    if exercise is not None:
        exercise["stage"] = fresh_stage_no
        return exercise

    raise ValueError(
        f"Could not generate a valid Stage {fresh_stage_no} exercise after {max_attempts} attempts."
    )


def choose_next_mode() -> str:
    """Auto mode: first make sure every skill gets practiced, then the weakest."""
    attempts = get_recent_attempts(15)
    recent_modes = [a.get("exercise_type") for a in attempts]

    # Any skill not practiced recently goes first, so Auto rotates
    # through all six skills instead of always picking Grammar.
    for mode in SKILL_MODES:
        if mode not in recent_modes:
            return mode

    scores: Dict[str, int] = {}
    for mode in SKILL_MODES:
        mode_scores = [
            safe_int(a.get("score"))
            for a in attempts
            if a.get("exercise_type") == mode
        ]
        if mode_scores:
            scores[mode] = round(sum(mode_scores) / len(mode_scores))

    if scores:
        return min(scores, key=scores.get)

    return SKILL_MODES[len(recent_modes) % len(SKILL_MODES)]


# -----------------------------
# Conversation history
# -----------------------------
def load_legacy_history_for_context(limit: int = 12) -> List[Dict[str, str]]:
    """Fetch the most recent conversation history from the new table."""
    try:
        result = (
            supabase.table("chat_messages")
            .select("role, content")
            .eq("learner_id", LEARNER_ID)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(result.data or []))
        return [
            {"role": row.get("role", "assistant"), "content": row.get("content", "")}
            for row in rows
        ]
    except Exception:
        return []


# -----------------------------
# Session state
# -----------------------------
if "current_exercise" not in st.session_state:
    st.session_state.current_exercise = None
if "session_started" not in st.session_state:
    st.session_state.session_started = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "lesson_concept" not in st.session_state:
    st.session_state.lesson_concept = None
if "lesson_mode" not in st.session_state:
    # The real skill used for the lesson (Auto resolves to one skill).
    st.session_state.lesson_mode = None
if "lesson_mode_choice" not in st.session_state:
    # What was selected in the dropdown when the lesson was created
    # (can be "Auto"). Used to detect a dropdown change.
    st.session_state.lesson_mode_choice = None
if "taught_concept_topics" not in st.session_state:
    st.session_state.taught_concept_topics = []


def handle_mode_change() -> None:
    """A mode change starts a clean learning context."""
    reset_lesson_state()


with st.expander("🕘 Recent coach messages"):
    history = load_legacy_history_for_context(limit=12)
    if history:
        for msg in history:
            role = "You" if msg["role"] == "user" else "Coach"
            st.markdown(f"**{role}:** {msg['content']}")
    else:
        st.caption("No previous conversation history found.")


# -----------------------------
# Sidebar — dashboard
# -----------------------------
progress = refresh_derived_progress()
stage_no = safe_int(progress.get("current_stage"), 1)
stage = get_stage(stage_no)

st.sidebar.title("🎯 German Master Coach")

# Gemini model selector
model_labels = list(MODEL_OPTIONS.keys())
model_values = list(MODEL_OPTIONS.values())

if "gemini_model" not in st.session_state:
    default_model = GEMINI_MODEL if GEMINI_MODEL in model_values else model_values[0]
    st.session_state.gemini_model = default_model

current_model = st.session_state.gemini_model
current_index = model_values.index(current_model) if current_model in model_values else 0

selected_model_label = st.sidebar.selectbox(
    "🤖 Gemini model",
    model_labels,
    index=current_index,
    key="gemini_model_selector",
    help=(
        "Choose which Gemini model generates lessons, exercises, and grading. "
        "The selected model is used immediately for new AI calls."
    ),
)
st.session_state.gemini_model = MODEL_OPTIONS[selected_model_label]
st.sidebar.caption(f"Active: `{st.session_state.gemini_model}`")

st.sidebar.metric(
    "Current Stage",
    f"{stage_no}/{len(CURRICULUM)}",
    stage["level"],
)

# Manual level selection
st.sidebar.markdown("### 🎚️ Choose my level")
stage_labels = [
    f"Stage {s['stage']}: {s['level']} — {s['title']}" for s in CURRICULUM
]
# No widget key on purpose: when the stage changes automatically
# (promotion/downgrade), the default index changes and the picker follows it.
chosen_label = st.sidebar.selectbox(
    "Your level",
    stage_labels,
    index=stage_no - 1,
    help="Complete beginner? Stay at Stage 1 (A1). You move up automatically when you are ready.",
)
chosen_stage = stage_labels.index(chosen_label) + 1

if chosen_stage != stage_no:
    st.sidebar.caption(
        f"You are currently in Stage {stage_no}. Mastery for the new stage starts at 0%."
    )
    if st.sidebar.button(f"✅ Switch to Stage {chosen_stage}", use_container_width=True):
        set_stage_manually(chosen_stage)
        st.rerun()

# Passing rule: percentage or Goethe standard (saved with the Study Hub state)
st.sidebar.markdown("### 🎯 Passing rule")
current_mode, current_percent = pass_rule()
chosen_mode = st.sidebar.radio(
    "How do you pass a level?", list(PASS_MODE_LABELS), format_func=PASS_MODE_LABELS.get,
    index=list(PASS_MODE_LABELS).index(current_mode), key="pass_mode",
)
chosen_percent = current_percent
if chosen_mode == "percentage":
    chosen_percent = st.sidebar.select_slider(
        "Pass mark", PERCENT_CHOICES, value=current_percent, format_func=lambda p: f"{p}%", key="pass_percent",
        help="Average score you need over your last 8–20 exercises in this stage.",
    )
else:
    st.sidebar.caption(
        "Like the real Goethe-Zertifikat: you need 60%+ in **each** exam skill (Lesen, Hören, Schreiben, "
        "Sprechen). A strong skill can't make up for a weak one."
    )
if (chosen_mode, chosen_percent) != (current_mode, current_percent):
    hub_state = hub_load()
    hub_state["pass_rule"] = {"mode": chosen_mode, "percent": chosen_percent}
    hub_save(hub_state)
    st.rerun()

if stage_no < len(CURRICULUM):
    if chosen_mode == "goethe":
        stage_attempts_now = [a for a in get_recent_attempts(300) if safe_int(a.get("stage")) == stage_no]
        lines_ = []
        for skill, (n, avg) in goethe_module_scores(stage_attempts_now).items():
            ok = n >= GOETHE_MIN_PER_MODULE and avg is not None and avg >= GOETHE_PASS
            shown = f"{avg}%" if avg is not None else "—"
            lines_.append(f"{'✅' if ok else '⬜'} {GOETHE_MODULES[skill]}: {shown} ({min(n, GOETHE_MIN_PER_MODULE)}/{GOETHE_MIN_PER_MODULE})")
        st.sidebar.caption(f"🚀 Jump to Stage {stage_no + 1}:  \n" + "  \n".join(lines_))
    else:
        evidence_count, evidence_avg = get_promotion_evidence(stage_no)
        st.sidebar.caption(
            f"🚀 Jump to Stage {stage_no + 1}: {min(evidence_count, 8)}/8 exercises, "
            f"average {evidence_avg}% (need {chosen_percent}%)"
        )

if "Downgraded" in str(progress.get("status", "")):
    st.sidebar.warning(
        "Your recent performance triggered a stage review/downgrade. "
        "You can advance again by proving mastery."
    )

st.sidebar.progress(safe_int(progress.get("stage_mastery")) / 100)
st.sidebar.caption(f"Stage mastery: {progress.get('stage_mastery', 0)}%")

st.sidebar.progress(safe_int(progress.get("overall_mastery")) / 100)
st.sidebar.caption(f"Overall mastery: {progress.get('overall_mastery', 0)}%")

st.sidebar.metric(
    "Study time",
    f"{safe_int(progress.get('total_study_minutes')) // 60}h "
    f"{safe_int(progress.get('total_study_minutes')) % 60}m",
)

st.sidebar.metric(
    "Study streak",
    f"{safe_int(progress.get('current_streak'))} days",
)

weak = progress.get("weak_areas") or []
st.sidebar.markdown("### 🔴 Weak areas")
st.sidebar.write(", ".join(weak) if weak else "Not enough data yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("### Current target")
st.sidebar.write(stage["title"])

for skill in SKILL_MODES:
    st.sidebar.caption(f"**{skill}:** " + ", ".join(get_mode_topics(stage, skill)))


# -----------------------------
# Session timer
# -----------------------------
st.title("🇩🇪 German Master Coach")
st.caption(
    f"Adaptive A1 → B2 training with {st.session_state.get('gemini_model', GEMINI_MODEL)}. "
    "Your previous learning history is preserved. Extra study time means extra practice. "
    "You advance when your measured mastery proves you are ready."
)

timer_col1, timer_col2, timer_col3 = st.columns(3)

with timer_col1:
    if st.session_state.session_started is None:
        if st.button("▶️ Start study session", use_container_width=True):
            st.session_state.session_started = time.time()
            st.rerun()
    else:
        if st.button("⏹️ Finish study session", use_container_width=True):
            elapsed = int((time.time() - st.session_state.session_started) / 60)
            elapsed = max(1, elapsed)
            add_study_minutes(elapsed)
            st.session_state.session_started = None
            st.success(f"Saved {elapsed} minutes to Supabase.")
            st.rerun()

with timer_col2:
    if st.session_state.session_started:
        elapsed = int((time.time() - st.session_state.session_started) / 60)
        st.metric("Current session", f"{elapsed} min")
    else:
        st.metric("Current session", "Not running")

with timer_col3:
    st.metric(
        "Attempts",
        safe_int(progress.get("lifetime_attempts")),
    )


# -----------------------------
# Automatic stage announcement
# -----------------------------
downgrade_message = st.session_state.pop("downgrade_message", None)
if downgrade_message:
    st.error(downgrade_message)

unlock_message = st.session_state.pop("unlock_message", None)
if unlock_message:
    st.success(unlock_message)


# -----------------------------
# Lesson-first learning flow
# -----------------------------
st.markdown("## 📚 Today's adaptive lesson")

mode_options = ["Auto"] + SKILL_MODES
mode_choice = st.selectbox(
    "Choose exercise type",
    mode_options,
    index=0,
    key="exercise_mode_selector",
    on_change=handle_mode_change,
)

# HARD MODE/LESSON CONSISTENCY GUARD
# Compare against the dropdown value that created the lesson (which may be
# "Auto"), not the resolved skill — otherwise Auto lessons vanish on rerun.
if st.session_state.get("lesson_concept"):
    if st.session_state.get("lesson_mode_choice") != mode_choice:
        reset_lesson_state()


def start_new_lesson(previous_concept: Optional[Dict[str, Any]] = None) -> None:
    selected_mode = choose_next_mode() if mode_choice == "Auto" else mode_choice
    with st.spinner(f"Preparing a {selected_mode} lesson..."):
        fresh_progress = refresh_derived_progress()
        concept = generate_lesson_concept(
            fresh_progress, selected_mode, previous_concept=previous_concept
        )
    st.session_state.lesson_concept = concept
    st.session_state.lesson_mode = selected_mode
    st.session_state.lesson_mode_choice = mode_choice
    st.session_state.current_exercise = None
    st.session_state.last_result = None


def start_exercise() -> None:
    selected_mode = st.session_state.lesson_mode or (
        choose_next_mode() if mode_choice == "Auto" else mode_choice
    )
    with st.spinner(f"Creating a {selected_mode} exercise..."):
        fresh_progress = refresh_derived_progress()
        st.session_state.current_exercise = generate_unique_exercise(
            fresh_progress, selected_mode
        )
    st.session_state.last_result = None


col_a, col_b = st.columns([1, 1])

with col_a:
    if st.button("📘 Teach me a concept first", use_container_width=True):
        try:
            start_new_lesson()
            st.rerun()
        except Exception as exc:
            st.error(f"Could not prepare lesson: {exc}")

with col_b:
    if st.button("🔴 Teach me my weakest area", use_container_width=True):
        try:
            start_new_lesson()
            st.rerun()
        except Exception as exc:
            st.error(f"Could not prepare lesson: {exc}")

# -----------------------------
# Teach concept BEFORE exercise
# -----------------------------
concept = st.session_state.lesson_concept
if concept and not st.session_state.current_exercise:
    lesson_mode = st.session_state.lesson_mode or "Grammar"
    st.markdown("---")
    st.markdown(f"### 📖 {concept.get('title', 'Concept lesson')}")
    st.caption(f"Skill: **{lesson_mode}** · Concept: **{concept.get('topic', '')}**")
    st.write(concept.get("explanation", ""))

    rules = concept.get("rules") or []
    if rules:
        heading = {
            "Grammar": "🧠 Key rules",
            "Vocabulary": "🗂️ Words & phrases",
            "Listening": "👂 Listening tips & key phrases",
            "Reading": "📑 Reading tips & key words",
            "Writing": "📝 Structure & useful phrases",
            "Speaking": "🗣️ Useful phrases",
        }.get(lesson_mode, "🧠 Key points")
        st.markdown(f"#### {heading}")
        for rule in rules:
            st.markdown(f"- {str(rule).strip()}")

    sample_text = str(concept.get("sample_text") or "").strip()
    if sample_text:
        if lesson_mode == "Listening":
            st.markdown("#### 🎧 Listen")
            german_audio(sample_text)
            with st.expander("Show transcript"):
                st.write(sample_text)
        else:
            st.markdown("#### 📄 Model text")
            st.write(sample_text)
            if lesson_mode == "Speaking":
                german_audio(sample_text)

    examples = concept.get("examples") or []
    if examples:
        st.markdown("#### ✍️ Examples")
        for ex in examples:
            if not isinstance(ex, dict):
                st.markdown(f"- {ex}")
                continue
            german = ex.get("german", "")
            english = ex.get("english", "")
            note = ex.get("note", "")
            st.markdown(f"**German:** {german}")
            if english:
                st.caption(f"English: {english}")
            if note:
                st.caption(f"💡 {note}")

    mistakes = concept.get("common_mistakes") or []
    if mistakes:
        st.markdown("#### ⚠️ Common mistakes")
        for mistake in mistakes:
            st.markdown(f"- {mistake}")

    if concept.get("quick_check"):
        st.markdown("#### 🔎 Quick check")
        st.info(concept["quick_check"])

    if st.button("🚀 I understand — give me an exercise", type="primary", use_container_width=True):
        try:
            start_exercise()
            st.rerun()
        except Exception as exc:
            st.error(f"Could not generate exercise: {exc}")

if not st.session_state.lesson_concept and not st.session_state.current_exercise:
    st.caption("Start with **Teach me a concept first** so the coach explains the concept before practice.")

# -----------------------------
# Render current exercise
# -----------------------------
exercise = st.session_state.current_exercise

if exercise:
    st.markdown("---")

    mode = exercise.get("mode", "Grammar")
    topic = exercise.get("topic", "General")

    st.markdown(f"### {mode} · {topic}")
    st.info(exercise.get("question", ""))

    if mode == "Listening":
        transcript = exercise.get("transcript", "")
        if transcript:
            st.caption("🎧 Listen carefully. The transcript is hidden until you submit.")
            german_audio(transcript)

    # Key keeps the input tied to this generated exercise.
    exercise_key = f"answer_{hash(exercise.get('question', ''))}"

    user_answer = st.text_area(
        "Your answer in German",
        key=exercise_key,
        height=160 if mode in ("Writing", "Speaking") else 100,
        placeholder="Schreibe deine Antwort hier auf Deutsch …",
    )

    if mode == "Speaking":
        audio = st.audio_input(
            "🎙️ Optional: record your German",
            sample_rate=16000,
            key=f"audio_{hash(exercise.get('question', ''))}",
        )
        if audio:
            st.audio(audio)

    if st.button("✅ Submit answer", type="primary"):
        if not user_answer.strip():
            st.warning("Please write an answer first.")
        else:
            with st.spinner("Grading your German..."):
                result = grade_answer(exercise, user_answer)

            if mode == "Listening" and exercise.get("transcript"):
                result["transcript"] = exercise["transcript"]

            st.session_state.last_result = result

            save_attempt(
                exercise_type=mode,
                topic=topic,
                stage=safe_int(exercise.get("stage"), stage_no),
                prompt_text=exercise.get("question", ""),
                user_answer=user_answer,
                score=result["score"],
                correct=result["correct"],
                explanation=result.get("explanation", ""),
            )

            # Count this result toward its grammar syllabus point (Study Hub ticks itself).
            if mode == "Grammar" and result.get("grammar_point"):
                record_grammar_point(result["grammar_point"], result["score"])

            if not result["correct"] or result["score"] < 85:
                error_topic = result.get("main_error_topic") or topic
                save_mistake(
                    topic=error_topic,
                    mistake_text=result.get("error_text") or user_answer,
                    correction=result.get("corrected_answer") or "",
                    explanation=result.get("explanation") or "",
                )

            refresh_derived_progress()

            # The submitted exercise is now completed.
            st.session_state.current_exercise = None
            st.rerun()


# -----------------------------
# Result
# -----------------------------
result = st.session_state.last_result

if result:
    st.markdown("---")
    st.caption("✅ This exercise has been recorded. Generate next exercise for a new task.")
    score = safe_int(result.get("score"))

    if score >= pass_mark():
        st.success(f"✅ {score}/100 — Passed")
    elif score >= pass_mark() - 15:
        st.warning(f"🟠 {score}/100 — Good, but review needed")
    else:
        st.error(f"🔴 {score}/100 — Needs more practice")

    if result.get("transcript"):
        with st.expander("🎧 Listening transcript"):
            st.write(result["transcript"])

    corrected = result.get("corrected_answer")
    explanation = result.get("explanation")

    if corrected:
        st.markdown("**Correction / better answer:**")
        st.write(corrected)

    if explanation:
        st.markdown("**Why:**")
        st.write(explanation)

    if result.get("improved_version"):
        st.markdown("**More natural German:**")
        st.write(result["improved_version"])

    # Recalculate and check automatic advancement immediately.
    progress = refresh_derived_progress()

    if can_advance_stage(progress):
        new_progress, advanced, message = advance_stage_if_ready()
        if advanced:
            st.session_state.unlock_message = message
            reset_lesson_state()
            st.rerun()

    st.markdown("### 📈 Updated progress")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("Stage mastery", f"{progress.get('stage_mastery', 0)}%")
    with p2:
        st.metric("Overall mastery", f"{progress.get('overall_mastery', 0)}%")
    with p3:
        st.metric("Status", progress.get("status", "On Track"))


# -----------------------------
# Continue the lesson / choose a new concept
# -----------------------------
if st.session_state.lesson_concept:
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Practice this concept again", use_container_width=True):
            try:
                start_exercise()
                st.rerun()
            except Exception as exc:
                st.error(f"Could not generate exercise: {exc}")
    with c2:
        if st.button("📘 Learn a new concept", use_container_width=True):
            try:
                start_new_lesson(previous_concept=st.session_state.lesson_concept)
                st.rerun()
            except Exception as exc:
                st.error(f"Could not prepare new lesson: {exc}")


# -----------------------------
# Skill dashboard
# -----------------------------
st.markdown("---")
st.markdown("## 🧠 Skill dashboard")

attempts = get_recent_attempts(500)

# One dashboard per level. Defaults to the current stage; no widget key on
# purpose so the default follows automatic promotion/downgrade.
dashboard_labels = [
    f"Stage {s['stage']}: {s['level']} — {s['title']}" for s in CURRICULUM
] + ["All levels combined"]
dashboard_label = st.selectbox(
    "Show skills for",
    dashboard_labels,
    index=stage_no - 1,
)

if dashboard_label == "All levels combined":
    dashboard_attempts = attempts
else:
    dashboard_stage = dashboard_labels.index(dashboard_label) + 1
    dashboard_attempts = [
        a for a in attempts if safe_int(a.get("stage")) == dashboard_stage
    ]

skill_cols = st.columns(6)
for col, skill in zip(skill_cols, SKILL_MODES):
    with col:
        score = compute_skill_score(dashboard_attempts, skill)
        count = sum(1 for a in dashboard_attempts if a.get("exercise_type") == skill)
        st.metric(skill, f"{score}%" if score is not None else "—")
        st.caption(f"{count} exercise{'s' if count != 1 else ''}")

if not dashboard_attempts:
    st.caption("No exercises recorded for this level yet.")

# Overview table: every level × every skill.
with st.expander("📊 All levels at a glance"):
    rows = []
    for item in CURRICULUM:
        item_attempts = [
            a for a in attempts if safe_int(a.get("stage")) == item["stage"]
        ]
        row = {"Level": f"Stage {item['stage']} ({item['level']})"}
        for skill in SKILL_MODES:
            score = compute_skill_score(item_attempts, skill)
            row[skill] = f"{score}%" if score is not None else "—"
        rows.append(row)
    st.dataframe(rows, hide_index=True, use_container_width=True)


# -----------------------------
# Study Hub — week-by-week plan, topic progress per level, roadmap
# -----------------------------
# Ticked sessions are stored in the Supabase table `study_hub`:
#   create table if not exists study_hub (
#     learner_id text primary key,
#     data jsonb not null default '{}'::jsonb,
#     updated_at timestamptz default now()
#   );
# Without that table, ticks only last for the current browser session.
# Word Rain vocabulary is synced by the local German Tutor tools into:
#   create table if not exists word_memory (
#     learner_id text primary key,
#     data jsonb not null default '{}'::jsonb,
#     updated_at timestamptz default now()
#   );
HUB_MINUTES = {"TEACH": 45, "PRACTICE": 40, "WORDS": 30, "REVIEW": 45, "CHECK": 45}
HUB_MASTER_SCORE = 85
HUB_MASTER_MIN_ATTEMPTS = 3
HUB_STATUS_ICON = {"mastered": "✅ Mastered", "learning": "🟡 Learning", "not_started": "⚪ Not started"}


def hub_level_for_stage(stage_number: int) -> str:
    return ("A1" if stage_number <= 1 else "A2" if stage_number <= 3
            else "B1" if stage_number <= 5 else "B2")


def hub_grammar_topic_stage(topic: Optional[str]) -> Optional[int]:
    for item in CURRICULUM:
        if topic in get_mode_topics(item, "Grammar"):
            return item["stage"]
    return None


def hub_grammar_status(
    all_attempts: List[Dict[str, Any]], point_id: str, topic: Optional[str]
) -> Tuple[str, str]:
    """Automatic status of one grammar point, plus a short note.

    Uses the exercises aimed at this exact point. Exercises from before points
    were tracked only count through their topic: a mastered topic marks all
    its points as mastered.
    """
    status, n, avg = grammar_point_status(point_id)
    if status == "mastered":
        return "mastered", f"{n} exercises · {avg}%"
    stage_number = hub_grammar_topic_stage(topic)
    if topic and stage_number:
        ts = hub_topic_stats(all_attempts, stage_number, "Grammar", topic)
        if ts["status"] == "mastered":
            return "mastered", "topic mastered"
    if status == "learning":
        return "learning", f"{n} exercises · {avg}%"
    return "not_started", ""


def hub_load_word_memory() -> Optional[Dict[str, Any]]:
    """Word Rain memory synced from the local tools (Supabase table `word_memory`)."""
    if "hub_word_memory" not in st.session_state:
        data = None
        try:
            res = (
                supabase.table("word_memory").select("data, updated_at")
                .eq("learner_id", LEARNER_ID).limit(1).execute()
            )
            if res.data:
                data = res.data[0].get("data") or {}
                data["_updated_at"] = res.data[0].get("updated_at")
        except Exception:
            data = None
        st.session_state.hub_word_memory = data
    return st.session_state.hub_word_memory


def hub_toggle_grammar(point_id: str) -> None:
    state = hub_load()
    known = set(state.get("grammar_known") or [])
    if st.session_state.get(f"hubg_{point_id}"):
        known.add(point_id)
    else:
        known.discard(point_id)
    state["grammar_known"] = sorted(known)
    hub_save(state)


def hub_topic_stats(
    all_attempts: List[Dict[str, Any]], stage_number: int, skill: str, topic: str
) -> Dict[str, Any]:
    rows = [
        a for a in all_attempts
        if safe_int(a.get("stage")) == stage_number
        and a.get("exercise_type") == skill
        and normalize_answer(str(a.get("topic") or "")) == normalize_answer(topic)
    ]
    scores = [safe_int(a.get("score")) for a in rows]  # newest first
    n = len(scores)
    avg = round(sum(scores[:5]) / len(scores[:5])) if scores else None
    if n == 0:
        status, prog = "not_started", 0
    elif n >= HUB_MASTER_MIN_ATTEMPTS and avg >= HUB_MASTER_SCORE:
        status, prog = "mastered", 100
    else:
        # Grows with score and amount of practice; capped below "mastered".
        status = "learning"
        prog = min(95, round(avg * min(n, HUB_MASTER_MIN_ATTEMPTS) / HUB_MASTER_MIN_ATTEMPTS))
    return {
        "skill": skill, "topic": topic, "status": status, "exercises": n,
        "avg": avg, "progress": prog,
        "last": str(rows[0].get("created_at") or "")[:10] if rows else "",
    }


def hub_stage_rows(all_attempts: List[Dict[str, Any]], stage_number: int) -> List[Dict[str, Any]]:
    item = get_stage(stage_number)
    return [
        hub_topic_stats(all_attempts, stage_number, skill, topic)
        for skill in SKILL_MODES
        for topic in get_mode_topics(item, skill)
    ]


def hub_chunk(items: List[Any], n: int) -> List[List[Any]]:
    """Split items into n nearly equal, ordered parts (some may be empty)."""
    out, pos = [], 0
    for i in range(n):
        size = len(items) // n + (1 if i < len(items) % n else 0)
        out.append(items[pos:pos + size])
        pos += size
    return out


def hub_build_plan(start: date) -> List[Dict[str, Any]]:
    weeks: List[Dict[str, Any]] = []
    week_no = 1
    for item in CURRICULUM:
        first, last = (int(x) for x in str(item["weeks"]).replace("–", "-").split("-"))
        n = last - first + 1
        grammar = hub_chunk(get_mode_topics(item, "Grammar"), n)
        # Interleave the other skills so each week mixes them.
        per_skill = [[(sk, t) for t in get_mode_topics(item, sk)] for sk in SKILL_MODES if sk != "Grammar"]
        mixed = []
        for i in range(max(len(x) for x in per_skill)):
            mixed += [lst[i] for lst in per_skill if i < len(lst)]
        others = hub_chunk(mixed, n)
        for i in range(n):
            ws = start + timedelta(weeks=week_no - 1)
            sessions = []
            for t in grammar[i]:
                sessions.append({"kind": "TEACH", "skill": "Grammar", "topic": t, "title": f"Grammar: {t}",
                                 "sub": "Choose Grammar above → Teach me a concept first → 3+ exercises."})
            for sk, t in others[i]:
                sessions.append({"kind": "PRACTICE", "skill": sk, "topic": t, "title": f"{sk}: {t}",
                                 "sub": f"Choose {sk} above → lesson + 3 exercises."})
            if not grammar[i] and not others[i]:
                sessions.append({"kind": "REVIEW", "skill": None, "topic": None,
                                 "title": "Review your 2 weakest topics",
                                 "sub": "See the Topics tab: start with the lowest averages."})
            sessions.append({"kind": "WORDS", "skill": None, "topic": None,
                             "title": "Vocabulary: 3 short Word Rain rounds",
                             "sub": "Spread over the week. Short and often beats long."})
            if i == n - 1:
                sessions.append({
                    "kind": "CHECK", "skill": None, "topic": None,
                    "title": (f"Level check: ready for Stage {item['stage'] + 1}?"
                              if item["stage"] < len(CURRICULUM) else "Final check: full mock exam"),
                    "sub": f"You move up with: {pass_rule_text()}.",
                })
            for k, sess in enumerate(sessions):
                sess["id"] = f"w{week_no}-{k}-{sess['kind']}-{normalize_answer(sess['topic'] or sess['title'])}"
                sess["minutes"] = HUB_MINUTES[sess["kind"]]
            weeks.append({"week": week_no, "stage": item["stage"], "level": item["level"],
                          "stage_title": item["title"], "start": ws, "end": ws + timedelta(days=6),
                          "sessions": sessions})
            week_no += 1
    return weeks


def hub_toggle(session_id: str) -> None:
    state = hub_load()
    done_ids = set(state.get("done") or [])
    if st.session_state.get(f"hub_{session_id}"):
        done_ids.add(session_id)
    else:
        done_ids.discard(session_id)
    state["done"] = sorted(done_ids)
    hub_save(state)


st.markdown("""
<style>
.hub-eyebrow { font-family: ui-monospace, Consolas, monospace; letter-spacing: .14em;
  text-transform: uppercase; font-size: .78rem; opacity: .7; }
.hub-title { font-size: clamp(1.9rem, 5vw, 3rem); font-weight: 800; line-height: 1.05;
  margin: .25rem 0 .4rem; letter-spacing: -.02em; }
.hub-days { font-size: 1.35rem; font-weight: 700; }
.hub-days span { font-weight: 400; font-size: 1rem; opacity: .75; }
.hub-stats { display: grid; grid-template-columns: repeat(4, 1fr); margin: 1rem 0 .5rem;
  border-top: 2px solid rgba(128,128,128,.55); border-bottom: 2px solid rgba(128,128,128,.55); }
.hub-stat { padding: 14px 18px; border-left: 1px solid rgba(128,128,128,.3); }
.hub-stat:first-child { border-left: 0; padding-left: 0; }
.hub-stat b { display: block; font-family: ui-monospace, Consolas, monospace; font-size: 1.8rem; line-height: 1.2; }
.hub-stat b.text { font-family: inherit; font-size: 1.02rem; line-height: 1.35; }
.hub-stat span { opacity: .75; font-size: .9rem; }
@media (max-width: 760px) { .hub-stats { grid-template-columns: repeat(2, 1fr); }
  .hub-stat:nth-child(3) { border-left: 0; padding-left: 0; } }
.week-head { font-family: ui-monospace, Consolas, monospace; opacity: .75; font-size: .9rem; }
.week-title { font-weight: 700; font-size: 1.08rem; }
.tag { font-family: ui-monospace, Consolas, monospace; font-size: .72rem; letter-spacing: .08em;
  border: 1px solid currentColor; border-radius: 4px; padding: 1px 6px; margin-right: 8px; }
.tag-TEACH { color: #6f9bff; } .tag-PRACTICE { color: #c084fc; } .tag-WORDS { color: #34c27a; }
.tag-REVIEW { color: #f59e0b; } .tag-CHECK { color: #eab308; }
.sess-title { font-weight: 600; }
.sess-sub { opacity: .7; font-size: .9rem; }
.sess-min { font-family: ui-monospace, Consolas, monospace; opacity: .7; text-align: right; }
.hub-badge { font-size: .8rem; opacity: .85; margin-left: 6px; }
</style>
""", unsafe_allow_html=True)

st.markdown("---")
hub = hub_load()
hub_plan = hub_build_plan(date.fromisoformat(hub["start_date"]))
hub_manual_done = set(hub.get("done") or [])
hub_sessions = [s for w in hub_plan for s in w["sessions"]]

# Sessions that tick themselves from real results.
hub_word_rounds = [
    safe_int(h.get("t")) for h in ((hub_load_word_memory() or {}).get("history") or [])
]
hub_auto_done: set = set()
for w in hub_plan:
    week_start_ms = datetime.combine(w["start"], datetime.min.time()).timestamp() * 1000
    week_end_ms = week_start_ms + 7 * 24 * 3600 * 1000
    for s in w["sessions"]:
        if s["kind"] in ("TEACH", "PRACTICE"):
            if hub_topic_stats(attempts, w["stage"], s["skill"], s["topic"])["exercises"] >= 3:
                hub_auto_done.add(s["id"])
        elif s["kind"] == "WORDS":
            if sum(1 for t in hub_word_rounds if week_start_ms <= t < week_end_ms) >= 3:
                hub_auto_done.add(s["id"])
        elif s["kind"] == "CHECK" and stage_no > w["stage"]:
            hub_auto_done.add(s["id"])
hub_done = hub_manual_done | hub_auto_done
hub_today = date.today()
hub_this_week = next(
    (w for w in hub_plan if w["start"] <= hub_today <= w["end"]),
    hub_plan[0] if hub_today < hub_plan[0]["start"] else hub_plan[-1],
)

st.markdown(
    f'<div class="hub-eyebrow">📚 Study Hub · German {CURRICULUM[0]["level"].split(" ")[0]} → B2</div>'
    '<div class="hub-title">Your German, week by week</div>',
    unsafe_allow_html=True,
)
hg1, hg2, _ = st.columns([2, 2, 3])
with hg1:
    hub_goal_label = st.text_input("Goal", hub["goal_label"], key="hub_goal_label")
with hg2:
    hub_goal_date = st.date_input(
        "Goal date (edit when you book it)", date.fromisoformat(hub["goal_date"]),
        format="DD/MM/YYYY", key="hub_goal_date",
    )
if hub_goal_label != hub["goal_label"] or hub_goal_date.isoformat() != hub["goal_date"]:
    hub["goal_label"], hub["goal_date"] = hub_goal_label, hub_goal_date.isoformat()
    hub_save(hub)

st.markdown(
    f'<div class="hub-days">{max((hub_goal_date - hub_today).days, 0)} days left '
    f'<span>until {hub["goal_label"]} · plan week {hub_this_week["week"]} '
    f'({hub_this_week["start"]:%d %b}–{hub_this_week["end"]:%d %b})</span></div>',
    unsafe_allow_html=True,
)

hub_level_rows = hub_stage_rows(attempts, stage_no)
hub_level_mastered = sum(1 for r in hub_level_rows if r["status"] == "mastered")
hub_promo_scores = [safe_int(a.get("score")) for a in attempts if safe_int(a.get("stage")) == stage_no][:20]
hub_promo_avg = round(sum(hub_promo_scores) / len(hub_promo_scores)) if hub_promo_scores else 0
if pass_rule()[0] == "goethe":
    hub_modules = goethe_module_scores([a for a in attempts if safe_int(a.get("stage")) == stage_no])
    hub_passed = sum(1 for n, avg in hub_modules.values()
                     if n >= GOETHE_MIN_PER_MODULE and avg is not None and avg >= GOETHE_PASS)
    hub_promo_html = (f'<div class="hub-stat"><b>{hub_passed}/4 skills</b>'
                      f'<span>at {GOETHE_PASS}%+ (Goethe standard)</span></div>')
else:
    hub_promo_html = (f'<div class="hub-stat"><b>{min(len(hub_promo_scores), 8)}/8 · {hub_promo_avg}%</b>'
                      f'<span>toward next level (need {pass_mark()}%)</span></div>')
hub_next = next(
    (s for w in hub_plan if w["end"] >= hub_today for s in w["sessions"] if s["id"] not in hub_done),
    None,
)
hub_next_label = (
    f'W{next(w["week"] for w in hub_plan if hub_next in w["sessions"])}: {hub_next["title"]}'
    if hub_next else "All done 🎉"
)
st.markdown(
    '<div class="hub-stats">'
    f'<div class="hub-stat"><b>{len(hub_done & {s["id"] for s in hub_sessions})}/{len(hub_sessions)}</b>'
    '<span>sessions done</span></div>'
    f'<div class="hub-stat"><b>{hub_level_mastered}/{len(hub_level_rows)}</b>'
    f'<span>topics mastered in Stage {stage_no}</span></div>'
    + hub_promo_html +
    f'<div class="hub-stat"><b class="text">{hub_next_label}</b><span>next open session</span></div>'
    '</div>',
    unsafe_allow_html=True,
)
if not st.session_state.get("hub_db_ok", True):
    st.caption(
        "ℹ️ Ticks are only kept for this browser session. To save them, create the "
        "`study_hub` table in Supabase (SQL is in a comment in app.py above the Study Hub section)."
    )

hub_tab_syllabus, hub_tab_plan, hub_tab_topics, hub_tab_levels = st.tabs(
    ["Syllabus", "Plan", "Topics", "Levels"]
)

with hub_tab_syllabus:
    syl_levels = list(GRAMMAR_SYLLABUS)
    syl_level = st.radio(
        "Level", syl_levels, index=syl_levels.index(hub_level_for_stage(stage_no)),
        horizontal=True, key="hub_syl_level",
    )
    known_ids = set(hub.get("grammar_known") or [])
    points = []
    for name, example, topic in GRAMMAR_SYLLABUS[syl_level]:
        pid = grammar_point_id(syl_level, name)
        auto, note = hub_grammar_status(attempts, pid, topic)
        is_known = pid in known_ids or auto == "mastered"
        points.append({"id": pid, "name": name, "example": example, "topic": topic,
                       "auto": auto, "note": note, "known": is_known})
    g_known = sum(1 for p in points if p["known"])
    g_learning = sum(1 for p in points if not p["known"] and p["auto"] == "learning")

    # Vocabulary: the level's word list comes from Gemini; the vocab check measures what you know.
    vocab = vocab_load()
    v_list = (vocab.get("lists") or {}).get(syl_level) or {}
    v_topics: Dict[str, List[Dict[str, str]]] = v_list.get("topics") or {}
    v_words = [w for ws in v_topics.values() for w in ws]
    v_mem = vocab.get("mem") or {}
    v_known = sum(1 for w in v_words if vocab_status(v_mem.get(w["de"])) == "known")
    v_learning = sum(1 for w in v_words if vocab_status(v_mem.get(w["de"])) == "learning")

    sy1, sy2 = st.columns(2)
    with sy1:
        st.metric(f"🗂️ {syl_level} vocabulary", f"{v_known:,} / {len(v_words):,} words" if v_words else "no list yet",
                  f"{v_learning} learning" if v_learning else None, delta_color="off")
        st.progress(v_known / len(v_words) if v_words else 0)
    with sy2:
        st.metric(f"📐 {syl_level} grammar", f"{g_known} / {len(points)} points",
                  f"{g_learning} in progress" if g_learning else None, delta_color="off")
        st.progress(g_known / len(points) if points else 0)

    syl_tab_vocab, syl_tab_grammar = st.tabs(["🗂️ Vocabulary", "📐 Grammar"])

    with syl_tab_vocab:
        level_topics = vocab_level_topics(syl_level)
        if not st.session_state.get("vocab_db_ok", True):
            st.caption("ℹ️ The word list and your results only last for this browser session. To keep them, "
                       "create the `vocab` table in Supabase (SQL is in a comment in app.py).")
        missing_topics = [t for t in level_topics if not v_topics.get(t)]
        if missing_topics:
            st.info(
                f"Gemini builds your {syl_level} word list topic by topic "
                f"({', '.join(level_topics)}) and decides how many words each topic needs at this level."
                + (f" {len(missing_topics)} topic(s) still missing." if v_words else "")
            )
            if st.button(f"✨ Build my {syl_level} word list with Gemini", type="primary", key="vocab_build"):
                bar = st.progress(0.0, text="Asking Gemini…")
                failed = []
                for i, topic in enumerate(missing_topics, 1):
                    bar.progress((i - 1) / len(missing_topics), text=f"Gemini is listing words for: {topic}")
                    try:
                        existing = [w["de"] for w in v_words]
                        new_words = vocab_generate_topic(syl_level, topic, existing)
                        if new_words:
                            v_topics[topic] = new_words
                            v_words += new_words
                        else:
                            failed.append(topic)
                    except Exception:
                        failed.append(topic)
                    vocab.setdefault("lists", {})[syl_level] = {"topics": v_topics, "created": utc_now_iso()}
                    vocab_save(vocab)   # save after every topic, so nothing is lost
                bar.progress(1.0, text="Done")
                if failed:
                    st.session_state.vocab_build_failed = failed
                st.rerun()
            if st.session_state.get("vocab_build_failed"):
                st.warning("Gemini couldn't list words for: " + ", ".join(st.session_state.vocab_build_failed)
                           + ". Press the button again to retry.")

        if v_words:
            st.caption(
                f"Gemini's {syl_level} list has **{len(v_words)} words**. "
                "A word counts as **known** when you get it right the first time you see it, or on 2 different days. "
                "Nouns need der/die/das; ae/oe/ue/ss work for umlauts."
            )

            # ---- vocab check ----
            st.markdown("##### 🧠 Vocab check")
            check_result = st.session_state.get("vocab_check_result")
            if check_result:
                right = sum(1 for r in check_result if r["result"] == "correct")
                st.info(f"{right} / {len(check_result)} right.")
                for r in check_result:
                    icon = {"correct": "✅", "article": "⚠️", "close": "🟠", "wrong": "❌"}[r["result"]]
                    note = {"article": " (article!)", "close": " (small typo)"}.get(r["result"], "")
                    typed = (f" · you typed „{r['typed']}“"
                             if r["typed"] and r["result"] != "correct" else "")
                    st.markdown(f"{icon} {r.get('emoji', '')} {r['en']} → **{r['de']}**{note}{typed}")
                missed = [r for r in check_result if r["result"] != "correct"]
                if missed:
                    st.caption(
                        f"The {len(missed)} word(s) you missed are now 🟡 learning. They come back first in your "
                        "next checks until you get each one right on 2 different days. "
                        "Retrying them now helps, but only a right answer on another day makes a word ✅ known."
                    )
                nb1, nb2 = st.columns(2)
                if missed and nb1.button(f"🔁 Retry the {len(missed)} I missed", key="vocab_retry",
                                         use_container_width=True):
                    st.session_state.vocab_round = safe_int(st.session_state.get("vocab_round")) + 1
                    st.session_state.vocab_check_words = {
                        "level": syl_level, "round": st.session_state.vocab_round,
                        "words": [{k: r[k] for k in ("de", "en", "emoji", "ex", "topic") if k in r} for r in missed],
                    }
                    st.session_state.vocab_check_result = None
                    st.rerun()
                if nb2.button("Next 10 words ➜", key="vocab_next", use_container_width=True):
                    st.session_state.vocab_check_result = None
                    st.session_state.vocab_check_words = None
                    st.rerun()
            else:
                check_words = st.session_state.get("vocab_check_words")
                if not check_words or check_words.get("level") != syl_level:
                    # A new round number gives the form fresh, empty input fields.
                    st.session_state.vocab_round = safe_int(st.session_state.get("vocab_round")) + 1
                    check_words = {"level": syl_level,
                                   "words": vocab_pick_check(v_words, v_mem, VOCAB_CHECK_SIZE),
                                   "round": st.session_state.vocab_round}
                    st.session_state.vocab_check_words = check_words
                n_learning_waiting = sum(1 for w in v_words if vocab_status(v_mem.get(w["de"])) == "learning")
                if n_learning_waiting:
                    st.caption(f"🟡 {n_learning_waiting} learning word(s) waiting. Up to 4 come back in every check.")
                with st.form(f"vocab_check_{check_words['round']}"):
                    st.caption("Type the German word. Leave it empty if you don't know it, which counts as not known.")
                    answers = []
                    for i, w in enumerate(check_words["words"]):
                        tag = "🆕 " if vocab_status(v_mem.get(w["de"])) == "new" else ""
                        answers.append(st.text_input(f"{tag}{w.get('emoji', '')} {w['en']}",
                                                     key=f"vocab_ans_{check_words['round']}_{i}"))
                    if st.form_submit_button("Check my answers", type="primary"):
                        results = []
                        for w, typed in zip(check_words["words"], answers):
                            result = vocab_check_answer(typed, w["de"]) if typed.strip() else "wrong"
                            vocab_record(vocab, w["de"], result == "correct")
                            results.append({**w, "typed": typed.strip(), "result": result})
                        vocab_save(vocab)
                        st.session_state.vocab_check_result = results
                        st.rerun()

            # ---- per-topic progress + browse ----
            st.markdown("##### Progress by topic")
            topic_rows = []
            for t, ws in v_topics.items():
                k = sum(1 for w in ws if vocab_status(v_mem.get(w["de"])) == "known")
                lrn = sum(1 for w in ws if vocab_status(v_mem.get(w["de"])) == "learning")
                topic_rows.append({"Topic": t, "Known": k, "Learning": lrn, "Words": len(ws),
                                   "Progress": round(100 * k / len(ws)) if ws else 0})
            st.dataframe(
                topic_rows, hide_index=True, use_container_width=True,
                column_config={"Progress": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")},
            )
            with st.expander(f"📖 Browse the {syl_level} word list"):
                browse_topic = st.selectbox("Topic", list(v_topics), key="vocab_browse_topic")
                status_icon = {"known": "✅", "learning": "🟡", "new": "⚪"}
                st.dataframe(
                    [{"": status_icon[vocab_status(v_mem.get(w["de"]))], "German": w["de"], "English": w["en"],
                      "Example": w.get("ex", "")} for w in v_topics.get(browse_topic, [])],
                    hide_index=True, use_container_width=True,
                )

    with syl_tab_grammar:
        st.markdown(f"#### 📐 {syl_level} grammar checklist")
        st.caption(
            f"Ticks itself: Grammar exercises target the point you've practised least, and a point is ✅ "
            f"once you score {POINT_MASTER_SCORE}%+ on average over {POINT_MASTER_MIN}+ of its exercises. "
            "You can also tick points you already know."
        )
        for p in points:
            with st.container(border=True):
                gc1, gc2 = st.columns([0.5, 9])
                if p["auto"] == "mastered":
                    gc1.markdown("✅")
                else:
                    gc1.checkbox("I know this", value=p["id"] in known_ids, key=f"hubg_{p['id']}",
                                 on_change=hub_toggle_grammar, args=(p["id"],), label_visibility="collapsed")
                if p["auto"] == "mastered":
                    badge = f'<span class="hub-badge">✅ learned · {p["note"]}</span>'
                elif p["auto"] == "learning":
                    badge = f'<span class="hub-badge">🟡 {p["note"]}</span>'
                elif p["known"]:
                    badge = '<span class="hub-badge">✔ ticked</span>'
                else:
                    badge = ""
                practice = (f' · practise via Grammar → <i>{p["topic"]}</i>' if p["topic"] and p["auto"] != "mastered" else "")
                gc2.markdown(
                    f'<span class="sess-title">{p["name"]}</span>{badge}<br>'
                    f'<span class="sess-sub">„{p["example"]}“{practice}</span>',
                    unsafe_allow_html=True,
                )

with hub_tab_plan:
    st.write(
        "Each week covers this stage's topics across all six skills. Sessions tick themselves: "
        "a topic after 3+ exercises, Word Rain after 3 rounds that week, a level check once you move up. "
        "You can also tick sessions yourself."
    )
    hp1, _ = st.columns([2, 5])
    with hp1:
        hub_start = st.date_input(
            "Plan started (week 1)", date.fromisoformat(hub["start_date"]),
            format="DD/MM/YYYY", key="hub_start_date",
        )
    if hub_monday(hub_start).isoformat() != hub["start_date"]:
        hub["start_date"] = hub_monday(hub_start).isoformat()
        hub_save(hub)
        st.rerun()
    hub_show = st.radio("Show", ["This stage", "Next 4 weeks", "All weeks"], horizontal=True, key="hub_show")
    if hub_show == "This stage":
        hub_weeks = [w for w in hub_plan if w["stage"] == hub_this_week["stage"]]
    elif hub_show == "Next 4 weeks":
        hub_weeks = [w for w in hub_plan if w["week"] >= hub_this_week["week"]][:4]
    else:
        hub_weeks = hub_plan

    for w in hub_weeks:
        n_done = sum(1 for s in w["sessions"] if s["id"] in hub_done)
        mins = sum(s["minutes"] for s in w["sessions"])
        with st.container(border=True):
            wh1, wh2 = st.columns([6, 1])
            here = " 📍 this week" if w is hub_this_week else ""
            wh1.markdown(
                f'<span class="week-head">W{w["week"]} · {w["start"]:%d %b}–{w["end"]:%d %b} · '
                f'Stage {w["stage"]} ({w["level"]})</span>&nbsp;&nbsp;'
                f'<span class="week-title">{w["stage_title"]}{here}</span>',
                unsafe_allow_html=True,
            )
            wh2.markdown(
                f'<div class="sess-min">{n_done}/{len(w["sessions"])} · {mins // 60}h{mins % 60:02d}</div>',
                unsafe_allow_html=True,
            )
            for s in w["sessions"]:
                sc1, sc2, sc3 = st.columns([0.5, 8, 1])
                if s["id"] in hub_auto_done:
                    sc1.checkbox("done", value=True, disabled=True, key=f"hub_auto_{s['id']}",
                                 label_visibility="collapsed")
                else:
                    sc1.checkbox(
                        "done", value=s["id"] in hub_manual_done, key=f"hub_{s['id']}",
                        on_change=hub_toggle, args=(s["id"],), label_visibility="collapsed",
                    )
                badge = ""
                if s.get("topic") and s.get("skill"):
                    ts = hub_topic_stats(attempts, w["stage"], s["skill"], s["topic"])
                    if ts["status"] == "mastered":
                        badge = '<span class="hub-badge">✅ mastered</span>'
                    elif ts["status"] == "learning":
                        badge = f'<span class="hub-badge">🟡 {ts["exercises"]} exercises · {ts["avg"]}%</span>'
                elif s["id"] in hub_auto_done:
                    badge = '<span class="hub-badge">✅ done (auto)</span>'
                sc2.markdown(
                    f'<span class="tag tag-{s["kind"]}">{s["kind"]}</span>'
                    f'<span class="sess-title">{s["title"]}</span>{badge}<br>'
                    f'<span class="sess-sub">{s["sub"]}</span>',
                    unsafe_allow_html=True,
                )
                sc3.markdown(f'<div class="sess-min">{s["minutes"]} min</div>', unsafe_allow_html=True)

with hub_tab_topics:
    hub_labels = [f"Stage {s['stage']}: {s['level']} — {s['title']}" for s in CURRICULUM]
    hub_level_label = st.selectbox("Level", hub_labels, index=stage_no - 1, key="hub_topics_level")
    hub_level_no = hub_labels.index(hub_level_label) + 1
    t_rows = hub_stage_rows(attempts, hub_level_no)
    t_total = len(t_rows)
    t_mastered = sum(1 for r in t_rows if r["status"] == "mastered")
    t_learning = sum(1 for r in t_rows if r["status"] == "learning")
    t_remaining = sum(1 for r in t_rows if r["status"] == "not_started")
    t_pct = round(sum(r["progress"] for r in t_rows) / t_total) if t_total else 0
    tm1, tm2, tm3, tm4 = st.columns(4)
    tm1.metric("Level progress", f"{t_pct}%")
    tm2.metric("✅ Mastered", f"{t_mastered} / {t_total}")
    tm3.metric("🟡 Learning", t_learning)
    tm4.metric("⚪ Remaining", t_remaining)
    st.progress(t_pct / 100)

    # What to do next: weakest started topics first, then one new topic per skill.
    started = sorted((r for r in t_rows if r["status"] == "learning"), key=lambda r: r["avg"])[:3]
    new_per_skill: List[Dict[str, Any]] = []
    for r in t_rows:
        if r["status"] == "not_started" and all(x["skill"] != r["skill"] for x in new_per_skill):
            new_per_skill.append(r)
    t_next = (started + new_per_skill[:3])[:5]
    if t_next:
        st.markdown("#### ▶ Next up")
        for r in t_next:
            why = (f"average {r['avg']}% over {r['exercises']} exercise(s)"
                   if r["status"] == "learning" else "not started yet")
            st.markdown(f"- **{r['topic']}** · {r['skill']}: {why}")
    elif t_total:
        st.success("Every topic in this level is mastered. 🎉")

    skill_tabs = st.tabs([
        f"{sk} ({sum(1 for r in t_rows if r['skill'] == sk and r['status'] == 'mastered')}/"
        f"{sum(1 for r in t_rows if r['skill'] == sk)})"
        for sk in SKILL_MODES
    ])
    for tab, sk in zip(skill_tabs, SKILL_MODES):
        with tab:
            st.dataframe(
                [
                    {"Status": HUB_STATUS_ICON[r["status"]], "Topic": r["topic"],
                     "Exercises": r["exercises"], "Avg (last 5)": r["avg"],
                     "Progress": r["progress"], "Last practised": r["last"]}
                    for r in t_rows if r["skill"] == sk
                ],
                hide_index=True, use_container_width=True,
                column_config={
                    "Avg (last 5)": st.column_config.NumberColumn(format="%d%%"),
                    "Progress": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
                },
            )
    st.caption(
        f"✅ Mastered = {HUB_MASTER_MIN_ATTEMPTS}+ exercises averaging {HUB_MASTER_SCORE}%+ on the last 5. "
        "🟡 Learning = started but not there yet."
    )

with hub_tab_levels:
    level_rows = []
    for item in CURRICULUM:
        rows_i = hub_stage_rows(attempts, item["stage"])
        sessions_i = [s for w in hub_plan if w["stage"] == item["stage"] for s in w["sessions"]]
        marker = "✅" if item["stage"] < stage_no else "📍" if item["stage"] == stage_no else "🔒"
        level_rows.append({
            "Level": f"{marker} Stage {item['stage']}: {item['level']} — {item['title']}",
            "Weeks": item["weeks"],
            "Mastered": f"{sum(1 for r in rows_i if r['status'] == 'mastered')}/{len(rows_i)}",
            "Topic progress": round(sum(r["progress"] for r in rows_i) / len(rows_i)) if rows_i else 0,
            "Sessions done": f"{sum(1 for s in sessions_i if s['id'] in hub_done)}/{len(sessions_i)}",
        })
    st.dataframe(
        level_rows, hide_index=True, use_container_width=True,
        column_config={"Topic progress": st.column_config.ProgressColumn(
            min_value=0, max_value=100, format="%d%%")},
    )
    for item in CURRICULUM:
        with st.expander(f"Stage {item['stage']}: {item['level']} — {item['title']} (weeks {item['weeks']})"):
            for sk in SKILL_MODES:
                st.markdown(f"**{sk}:** " + ", ".join(get_mode_topics(item, sk)))


# -----------------------------
# Recent mistakes
# -----------------------------
mistakes = get_recent_mistakes(10)

with st.expander("🔴 Recent mistakes to review"):
    if not mistakes:
        st.write("No mistakes recorded yet.")
    else:
        for mistake in mistakes:
            st.markdown(
                f"**{mistake.get('topic', 'General')}** — "
                f"{mistake.get('mistake_text', '')}"
            )
            if mistake.get("correction"):
                st.write(f"✅ {mistake['correction']}")
            if mistake.get("explanation"):
                st.caption(mistake["explanation"])


# -----------------------------
# Grammar reference tables (toggle switches)
# -----------------------------
st.markdown("---")
render_grammar_tables()


# -----------------------------
# Advanced — reset
# -----------------------------
with st.expander("⚠️ Advanced"):
    st.caption("Deletes all your exercises, mistakes, plan ticks, vocabulary results and progress. "
               "This cannot be undone.")
    confirm_delete = st.checkbox("Yes, I really want to delete all my learning data.")
    if st.button("Delete my learning data", disabled=not confirm_delete):
        for table in ["exercise_attempts", "mistakes", "chat_messages", "study_hub", "vocab", "word_memory"]:
            try:
                supabase.table(table).delete().eq("learner_id", LEARNER_ID).execute()
            except Exception:
                pass
        supabase.table("learner_progress").delete().eq("learner_id", LEARNER_ID).execute()
        st.session_state.clear()
        st.success("Learning data deleted.")
        st.rerun()
