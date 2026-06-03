-- =============================================================================
-- VYNTRA Academic — Complete DDL + Seed for Supabase
-- Execute from Supabase Dashboard > SQL Editor
-- =============================================================================
-- NOTE: Run migrations/001_schema_optimizer.sql first if upgrading from v4

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 0: Grants — restricted; only service_role gets full access.
-- anon key only gets RLS-limited access.
-- ─────────────────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA public TO service_role, anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO anon, authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 0b: Create a secure read-only function for the AI agent
-- ─────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.run_readonly_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  result JSONB;
  allowed_tables TEXT[] := ARRAY['profiles','subjects','grades','student_metadata','class_materials','guides','notices','exams','exam_progress','risk_alerts','conversations'];
  query_lower TEXT;
  has_table BOOLEAN := false;
  t TEXT;
BEGIN
  query_lower := lower(query_text);

  -- Only SELECT allowed
  IF NOT (query_lower ~ '^select ') THEN
    RETURN jsonb_build_object('error', 'Solo se permiten consultas SELECT.');
  END IF;

  -- Check table references
  FOREACH t IN ARRAY allowed_tables
  LOOP
    IF query_lower ~ ('\m' || t || '\M') THEN
      has_table := true;
      EXIT;
    END IF;
  END LOOP;

  IF NOT has_table THEN
    RETURN jsonb_build_object('error', 'La consulta no referencia ninguna tabla permitida.');
  END IF;

  -- Block dangerous keywords
  IF query_lower ~ '\m(drop|truncate|delete|insert|update|alter|create|grant|revoke|exec|execute|call|fetch|copy|declare|raise|notify|listen)\M' THEN
    RETURN jsonb_build_object('error', 'Operación no permitida.');
  END IF;

  -- Execute with statement_timeout
  BEGIN
    SET LOCAL statement_timeout = '5000';
    EXECUTE 'SELECT coalesce(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ' LIMIT 100) t' INTO result;
    RETURN result;
  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('error', SQLERRM);
  END;
END;
$$;

REVOKE ALL ON FUNCTION public.run_readonly_query FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.run_readonly_query TO service_role, authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 1: Tables that might NOT exist yet
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.abp_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  linked_subject_ids UUID[] DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT true,
  project_trigger_keyword TEXT DEFAULT 'abp',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.project_abp_deliverables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  project_id UUID REFERENCES public.abp_projects(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES public.subjects(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL DEFAULT '',
  description TEXT DEFAULT '',
  file_url TEXT DEFAULT '',
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'approved', 'rejected')),
  progress_pct INTEGER DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
  score NUMERIC(3,2),
  feedback TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.behavior_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  log_type VARCHAR(20) NOT NULL CHECK (log_type IN ('positive', 'disciplinary', 'merit', 'observation')),
  description TEXT NOT NULL DEFAULT '',
  recorded_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS public.teacher_metadata (
  profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE PRIMARY KEY,
  specialty VARCHAR(100) DEFAULT '',
  bio TEXT DEFAULT '',
  office_hours VARCHAR(100) DEFAULT '',
  director_grade TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS public.class_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES public.courses(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES public.subjects(id) ON DELETE CASCADE,
  day_of_week INTEGER CHECK (day_of_week BETWEEN 1 AND 5),
  start_time TIME NOT NULL,
  end_time TIME NOT NULL
);

CREATE TABLE IF NOT EXISTS public.homework_reminders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES public.courses(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES public.subjects(id) ON DELETE CASCADE,
  title VARCHAR(150) NOT NULL,
  description TEXT DEFAULT '',
  due_date TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.academic_histories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  grade_name VARCHAR(20) NOT NULL,
  final_average NUMERIC(3,2) CHECK (final_average BETWEEN 0.0 AND 5.0),
  observations TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS public.mobile_push_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  device_token TEXT NOT NULL UNIQUE,
  device_type VARCHAR(20) CHECK (device_type IN ('ios', 'android')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  role VARCHAR(20) NOT NULL,
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_role ON public.conversations(user_id, role);

CREATE TABLE IF NOT EXISTS public.guides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  grade TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  title TEXT DEFAULT '',
  filename TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL DEFAULT '',
  teacher_id TEXT DEFAULT '',
  resource_type TEXT NOT NULL DEFAULT 'guide',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.class_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID REFERENCES public.subjects(id) ON DELETE CASCADE,
    grade_id TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'md',
    markdown_content TEXT DEFAULT '',
    cloudinary_url TEXT DEFAULT '',
    uploaded_by UUID REFERENCES public.profiles(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────
-- STEP 1b: Row-Level Security — restricted policies
-- ─────────────────────────────────────────────────────────────────────

-- Helper: drop old permissive policies
DO $$
DECLARE
  pol record;
BEGIN
  FOR pol IN
    SELECT policyname, tablename FROM pg_policies
    WHERE schemaname = 'public' AND policyname IN ('anon_all', 'class_materials_all_access')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', pol.policyname, pol.tablename);
  END LOOP;
END;
$$;

-- Profiles: users can read own, admins can read all
ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS profiles_select ON public.profiles;
CREATE POLICY profiles_select ON public.profiles FOR SELECT
  USING (auth.role() = 'service_role' OR id = auth.uid() OR auth.role() = 'authenticated');

-- Student metadata: own record + authenticated for related queries
ALTER TABLE IF EXISTS public.student_metadata ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS student_metadata_select ON public.student_metadata;
CREATE POLICY student_metadata_select ON public.student_metadata FOR SELECT
  USING (auth.role() = 'service_role' OR profile_id = auth.uid() OR auth.role() = 'authenticated');

-- Grades: own grades + authenticated for teachers
ALTER TABLE IF EXISTS public.grades ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS grades_select ON public.grades;
CREATE POLICY grades_select ON public.grades FOR SELECT
  USING (auth.role() = 'service_role' OR student_id = auth.uid() OR auth.role() = 'authenticated');

-- Rest of the tables: service_role only for write, authenticated can read
CREATE OR REPLACE FUNCTION public.create_restricted_policies()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  tbl TEXT;
  restricted_tables TEXT[] := ARRAY[
    'courses','subjects','teacher_assignments','exam_progress','class_schedules',
    'homework_reminders','teacher_metadata','academic_histories','mobile_push_tokens',
    'abp_projects','project_abp_deliverables','behavior_logs','conversations',
    'exams','exam_results','incident_reports','candidates','votes','deliveries',
    'guides','notices','class_materials'
  ];
BEGIN
  FOREACH tbl IN ARRAY restricted_tables
  LOOP
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
      EXECUTE format('DROP POLICY IF EXISTS %I_select ON public.%I', tbl, tbl);
      EXECUTE format('CREATE POLICY %I_select ON public.%I FOR SELECT USING (true)', tbl, tbl);
      EXECUTE format('DROP POLICY IF EXISTS %I_insert ON public.%I', tbl, tbl);
      EXECUTE format('DROP POLICY IF EXISTS %I_update ON public.%I', tbl, tbl);
      EXECUTE format('DROP POLICY IF EXISTS %I_delete ON public.%I', tbl, tbl);
    END IF;
  END LOOP;
END;
$$;
SELECT public.create_restricted_policies();

-- ─────────────────────────────────────────────────────────────────────
-- STEP 2: Add columns to existing tables (if missing)
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS password_hash TEXT,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS email TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS supabase_auth_id TEXT DEFAULT '';

ALTER TABLE public.student_metadata
  ADD COLUMN IF NOT EXISTS guardian_info TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS medical_notes TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS total_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS current_status TEXT NOT NULL DEFAULT 'AL_DIA',
  ADD COLUMN IF NOT EXISTS financial_override BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS financial_override_by TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS financial_override_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS wompi_customer_id VARCHAR(100) DEFAULT '',
  ADD COLUMN IF NOT EXISTS birth_date DATE,
  ADD COLUMN IF NOT EXISTS blood_type VARCHAR(5) DEFAULT '',
  ADD COLUMN IF NOT EXISTS guardian_name VARCHAR(150) DEFAULT '',
  ADD COLUMN IF NOT EXISTS guardian_phone VARCHAR(20) DEFAULT '';

ALTER TABLE public.courses
  ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS director_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;

ALTER TABLE public.subjects
  ADD COLUMN IF NOT EXISTS is_abp BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS syllabus JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS tutor_ai TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS planner_ai TEXT DEFAULT '';

ALTER TABLE public.teacher_assignments
  ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '';

ALTER TABLE public.grades
  ADD COLUMN IF NOT EXISTS observations TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS teacher_id TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS course_id TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS period TEXT NOT NULL DEFAULT 'P1';

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
-- STEP 4: Password Reset Codes table
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.password_reset_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL,
  login_credential TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.password_reset_codes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS password_reset_codes_select ON public.password_reset_codes;
CREATE POLICY password_reset_codes_select ON public.password_reset_codes FOR SELECT
  USING (auth.role() = 'service_role');

-- ─────────────────────────────────────────────────────────────────────
-- STEP 5: Clean existing seed data (child → parent) — comment out in production
-- ─────────────────────────────────────────────────────────────────────

DELETE FROM public.conversations;
DELETE FROM public.mobile_push_tokens;
DELETE FROM public.academic_histories;
DELETE FROM public.incident_reports;
DELETE FROM public.exam_results;
DELETE FROM public.exam_progress;
DELETE FROM public.project_abp_deliverables;
DELETE FROM public.behavior_logs;
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
DELETE FROM public.password_reset_codes;
DELETE FROM public.profiles;

-- ─────────────────────────────────────────────────────────────────────
-- STEP 6: Profiles (Rector, Teacher, 2 Students)
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.profiles (id, login_credential, fullname, role, password_hash) VALUES
  (gen_random_uuid(), '1',   'Rectora Ciudad del Sol',  'admin',   crypt('admin', gen_salt('bf', 10))),
  (gen_random_uuid(), '11',  'Profesor Titular Vyntra', 'teacher', crypt('profe', gen_salt('bf', 10))),
  (gen_random_uuid(), '101', 'Estudiante A - Sin Deuda', 'student', crypt('alumno', gen_salt('bf', 10))),
  (gen_random_uuid(), '102', 'Estudiante B - En Mora',   'student', crypt('alumno', gen_salt('bf', 10)));

-- ─────────────────────────────────────────────────────────────────────
-- STEP 7: Course
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.courses (id, name, academic_year, grade)
SELECT gen_random_uuid(), '11-A', 2026, '11-A';

-- ─────────────────────────────────────────────────────────────────────
-- STEP 8: Student Metadata
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
-- STEP 9: Subjects (9 ABP + 1 Traditional)
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.subjects (id, name, is_abp, grade)
SELECT gen_random_uuid(), name, is_abp, '11-A'
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
-- STEP 10: Teacher Assignments
-- ─────────────────────────────────────────────────────────────────────

INSERT INTO public.teacher_assignments (id, teacher_id, subject_id, course_id)
SELECT gen_random_uuid(), tp.id, s.id, c.id
FROM public.profiles tp
CROSS JOIN public.subjects s
CROSS JOIN (SELECT id FROM public.courses WHERE name = '11-A') c
WHERE tp.login_credential = '11';

-- ─────────────────────────────────────────────────────────────────────
-- STEP 11: Sample Grades
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
UNION ALL SELECT 'abp_projects', COUNT(*) FROM public.abp_projects
UNION ALL SELECT 'project_abp_deliverables', COUNT(*) FROM public.project_abp_deliverables
UNION ALL SELECT 'behavior_logs', COUNT(*) FROM public.behavior_logs
UNION ALL SELECT 'notices', COUNT(*) FROM public.notices
UNION ALL SELECT 'candidates', COUNT(*) FROM public.candidates
UNION ALL SELECT 'votes', COUNT(*) FROM public.votes
UNION ALL SELECT 'deliveries', COUNT(*) FROM public.deliveries
UNION ALL SELECT 'guides', COUNT(*) FROM public.guides
UNION ALL SELECT 'exam_results', COUNT(*) FROM public.exam_results
UNION ALL SELECT 'incident_reports', COUNT(*) FROM public.incident_reports
UNION ALL SELECT 'teacher_metadata', COUNT(*) FROM public.teacher_metadata
UNION ALL SELECT 'class_schedules', COUNT(*) FROM public.class_schedules
UNION ALL SELECT 'homework_reminders', COUNT(*) FROM public.homework_reminders
UNION ALL SELECT 'academic_histories', COUNT(*) FROM public.academic_histories
UNION ALL SELECT 'mobile_push_tokens', COUNT(*) FROM public.mobile_push_tokens
UNION ALL SELECT 'conversations', COUNT(*) FROM public.conversations
UNION ALL SELECT 'class_materials', COUNT(*) FROM public.class_materials;
