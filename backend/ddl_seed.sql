-- =============================================================================
-- VYNTRA Academic — Complete DDL + Seed for Supabase
-- Execute from Supabase Dashboard > SQL Editor
-- Uses service_role to bypass RLS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 0: Row-Level Security — allow service_role + anon access
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.student_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.teacher_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.exam_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.class_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.homework_reminders ENABLE ROW LEVEL SECURITY;

-- Allow full access for anon key (development only)
-- In production, restrict to service_role and authenticated users
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.profiles FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'student_metadata' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.student_metadata FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'courses' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.courses FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'subjects' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.subjects FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'teacher_assignments' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.teacher_assignments FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'grades' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.grades FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_progress' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.exam_progress FOR ALL USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'class_schedules' AND policyname = 'anon_all') THEN
    CREATE POLICY anon_all ON public.class_schedules FOR ALL USING (true) WITH CHECK (true);
  END IF;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 1: Tables that might NOT exist yet
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  grade TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  questions JSONB NOT NULL DEFAULT '[]'::jsonb,
  duration INTEGER NOT NULL DEFAULT 60,
  due_date TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  teacher_id TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.exam_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL,
  exam_id UUID NOT NULL,
  score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
  correct INTEGER NOT NULL DEFAULT 0,
  total INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.incident_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL,
  exam_id UUID NOT NULL,
  incident_type TEXT NOT NULL DEFAULT 'network_loss',
  severity TEXT NOT NULL DEFAULT 'low',
  description TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.notices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo TEXT NOT NULL,
  contenido TEXT NOT NULL,
  categoria TEXT NOT NULL DEFAULT 'General',
  archivo_url TEXT DEFAULT '',
  fecha TEXT NOT NULL DEFAULT '',
  author TEXT NOT NULL DEFAULT 'Rectoría',
  is_pinned BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  position TEXT NOT NULL,
  photo_url TEXT DEFAULT '',
  votes INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT NOT NULL DEFAULT '',
  grade TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  filename TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL DEFAULT '',
  teacher_id TEXT DEFAULT '',
  reviewed BOOLEAN NOT NULL DEFAULT false,
  review_score NUMERIC(5,2),
  date TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.guides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  grade TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  filename TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL DEFAULT '',
  teacher_id TEXT DEFAULT '',
  resource_type TEXT NOT NULL DEFAULT 'guide',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────
-- STEP 2: Add columns to existing tables (if missing)
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS password_hash TEXT,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.student_metadata
  ADD COLUMN IF NOT EXISTS guardian_info TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS medical_notes TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS total_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS current_status TEXT NOT NULL DEFAULT 'AL_DIA',
  ADD COLUMN IF NOT EXISTS financial_override BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS financial_override_by TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS financial_override_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.courses
  ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE public.subjects
  ADD COLUMN IF NOT EXISTS is_abp BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.teacher_assignments
  ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '';

ALTER TABLE public.grades
  ADD COLUMN IF NOT EXISTS observations TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS teacher_id TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS course_id TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.exam_progress
  ADD COLUMN IF NOT EXISTS current_question_index INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS time_elapsed_seconds INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_saved_at TIMESTAMPTZ;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 3: Drop profiles FK to auth.users (seed bypass)
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_type = 'FOREIGN KEY'
      AND table_schema = 'public'
      AND table_name = 'profiles'
  ) THEN
    EXECUTE (
      SELECT 'ALTER TABLE public.profiles DROP CONSTRAINT ' || constraint_name || ' CASCADE'
      FROM information_schema.table_constraints
      WHERE constraint_type = 'FOREIGN KEY'
        AND table_schema = 'public'
        AND table_name = 'profiles'
      LIMIT 1
    );
  END IF;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 4: Clean existing seed data (child → parent)
-- ─────────────────────────────────────────────────────────────────────

DELETE FROM public.incident_reports;
DELETE FROM public.exam_results;
DELETE FROM public.exam_progress;
DELETE FROM public.grades;
DELETE FROM public.class_schedules;
DELETE FROM public.homework_reminders;
DELETE FROM public.teacher_assignments;
DELETE FROM public.subjects;
DELETE FROM public.student_metadata;
DELETE FROM public.teacher_metadata;
DELETE FROM public.courses;
DELETE FROM public.votes;
DELETE FROM public.candidates;
DELETE FROM public.deliveries;
DELETE FROM public.guides;
DELETE FROM public.notices;
DELETE FROM public.exams;
DELETE FROM public.profiles;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 5: Profiles (Rector, Teacher, 2 Students)
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.profiles (id, login_credential, fullname, role, password_hash) VALUES
  (gen_random_uuid(), '1',   'Rectora Ciudad del Sol',  'admin',   crypt('admin', gen_salt('bf', 10))),
  (gen_random_uuid(), '11',  'Profesor Titular Vyntra', 'teacher', crypt('profe', gen_salt('bf', 10))),
  (gen_random_uuid(), '101', 'Estudiante A - Sin Deuda', 'student', crypt('alumno', gen_salt('bf', 10))),
  (gen_random_uuid(), '102', 'Estudiante B - En Mora',   'student', crypt('alumno', gen_salt('bf', 10)));

-- ─────────────────────────────────────────────────────────────────────
-- STEP 6: Course
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.courses (id, name, academic_year, grade)
SELECT gen_random_uuid(), '11-A', 2026, '11-A';

-- ─────────────────────────────────────────────────────────────────────
-- STEP 7: Student Metadata
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.student_metadata (profile_id, course_id, months_in_arrears, financial_override, guardian_info, medical_notes, total_balance, current_status)
SELECT p.id, c.id, 0, false, 'Padre: Carlos — Tel: 3001234567', 'Ninguna', 0.0, 'AL_DIA'
FROM public.profiles p
CROSS JOIN (SELECT id FROM public.courses WHERE name = '11-A') c
WHERE p.login_credential = '101';

INSERT INTO public.student_metadata (profile_id, course_id, months_in_arrears, financial_override, guardian_info, medical_notes, total_balance, current_status)
SELECT p.id, c.id, 3, false, 'Padre: María — Tel: 3007654321', 'Alergia al polen', 450000.0, 'EN_MORA'
FROM public.profiles p
CROSS JOIN (SELECT id FROM public.courses WHERE name = '11-A') c
WHERE p.login_credential = '102';

-- ─────────────────────────────────────────────────────────────────────
-- STEP 8: Subjects (9 ABP + 1 Traditional)
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.subjects (id, name, is_abp)
SELECT gen_random_uuid(), name, is_abp
FROM (VALUES
  ('Investigación Guiada',     true),
  ('Matemáticas Aplicadas',    true),
  ('Ciencias Naturales',       true),
  ('Lenguaje y Literatura',    true),
  ('Inglés Avanzado',          true),
  ('Ciencias Sociales',        true),
  ('Tecnología e Informática', true),
  ('Arte y Creatividad',       true),
  ('Música y Expresión',       true),
  ('Educación Física',         false)
) AS s(name, is_abp);

-- ─────────────────────────────────────────────────────────────────────
-- STEP 9: Teacher Assignments
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.teacher_assignments (id, teacher_id, subject_id, course_id)
SELECT gen_random_uuid(), tp.id, s.id, c.id
FROM public.profiles tp
CROSS JOIN public.subjects s
CROSS JOIN (SELECT id FROM public.courses WHERE name = '11-A') c
WHERE tp.login_credential = '11';

-- ─────────────────────────────────────────────────────────────────────
-- STEP 10: Sample Grades (tests ABP propagation trigger)
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.grades (student_id, subject_id, project_id, score)
SELECT p.id, s.id, gen_random_uuid(), 4.5
FROM public.profiles p
CROSS JOIN public.subjects s
WHERE p.login_credential = '101' AND s.is_abp = true AND s.name = 'Investigación Guiada';

INSERT INTO public.grades (student_id, subject_id, project_id, score)
SELECT p.id, s.id, gen_random_uuid(), 2.8
FROM public.profiles p
CROSS JOIN public.subjects s
WHERE p.login_credential = '102' AND s.is_abp = true AND s.name = 'Investigación Guiada';

-- ─────────────────────────────────────────────────────────────────────
-- Verification
-- ─────────────────────────────────────────────────────────────────────

SELECT 'profiles' AS tbl, COUNT(*) FROM public.profiles
UNION ALL SELECT 'student_metadata', COUNT(*) FROM public.student_metadata
UNION ALL SELECT 'courses', COUNT(*) FROM public.courses
UNION ALL SELECT 'subjects', COUNT(*) FROM public.subjects
UNION ALL SELECT 'teacher_assignments', COUNT(*) FROM public.teacher_assignments
UNION ALL SELECT 'grades', COUNT(*) FROM public.grades
UNION ALL SELECT 'exams', COUNT(*) FROM public.exams
UNION ALL SELECT 'notices', COUNT(*) FROM public.notices
UNION ALL SELECT 'candidates', COUNT(*) FROM public.candidates
UNION ALL SELECT 'votes', COUNT(*) FROM public.votes
UNION ALL SELECT 'deliveries', COUNT(*) FROM public.deliveries
UNION ALL SELECT 'guides', COUNT(*) FROM public.guides
UNION ALL SELECT 'exam_results', COUNT(*) FROM public.exam_results
UNION ALL SELECT 'incident_reports', COUNT(*) FROM public.incident_reports;
