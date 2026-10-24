-- German Master Coach: database tables for Supabase
-- Run once: Supabase → SQL Editor → New query → paste this whole file → Run.
-- Safe to run again (it only creates what is missing).

-- Your level, mastery, study time and streak (one row per learner)
create table if not exists learner_progress (
  learner_id          text primary key,
  current_stage       integer not null default 1,
  stage_mastery       integer not null default 0,
  overall_mastery     integer not null default 0,
  total_study_minutes integer not null default 0,
  lifetime_attempts   integer not null default 0,
  lifetime_correct    integer not null default 0,
  current_streak      integer not null default 0,
  longest_streak      integer not null default 0,
  last_study_date     date,
  weak_areas          jsonb   not null default '[]'::jsonb,
  status              text    not null default 'On Track',
  updated_at          timestamptz not null default now()
);

-- Every exercise you submit, with its score
create table if not exists exercise_attempts (
  id            bigint generated always as identity primary key,
  learner_id    text not null,
  exercise_type text,
  topic         text,
  stage         integer,
  prompt_text   text,
  user_answer   text,
  score         integer,
  correct       boolean,
  explanation   text,
  created_at    timestamptz not null default now()
);
create index if not exists exercise_attempts_learner_idx on exercise_attempts (learner_id, created_at desc);

-- Mistakes to review
create table if not exists mistakes (
  id           bigint generated always as identity primary key,
  learner_id   text not null,
  topic        text,
  mistake_text text,
  correction   text,
  explanation  text,
  reviewed     boolean not null default false,
  created_at   timestamptz not null default now()
);
create index if not exists mistakes_learner_idx on mistakes (learner_id, created_at desc);

-- Coach messages
create table if not exists chat_messages (
  id         bigint generated always as identity primary key,
  learner_id text not null,
  role       text,
  content    text,
  created_at timestamptz not null default now()
);
create index if not exists chat_messages_learner_idx on chat_messages (learner_id, id desc);

-- Study Hub: plan ticks, goal date, grammar checklist
create table if not exists study_hub (
  learner_id text primary key,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Gemini vocabulary lists and your vocab-check results
create table if not exists vocab (
  learner_id text primary key,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Optional: word memory synced from the local Word Rain game
create table if not exists word_memory (
  learner_id text primary key,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Security: switch on Row Level Security with no policies.
-- Then the public ("anon" / publishable) key can't read or change anything;
-- only your app, using the SECRET key from your Streamlit secrets, can.
alter table learner_progress  enable row level security;
alter table exercise_attempts enable row level security;
alter table mistakes          enable row level security;
alter table chat_messages     enable row level security;
alter table study_hub         enable row level security;
alter table vocab             enable row level security;
alter table word_memory       enable row level security;
