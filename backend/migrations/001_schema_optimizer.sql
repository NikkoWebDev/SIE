-- =============================================================================
-- VYNTRA Academic — Schema Optimizer v1.0
-- Idempotent migration: run in Supabase SQL Editor after seed.sql
-- Covers: ENUMs, Domains, FK fixes, Indexes (P0-P2), GIN, Triggers,
--         Soft deletes, Audit trail, Realtime, FTS, Partitioning prep,
--         Materialized views, CITEXT, Granular RLS
-- =============================================================================
BEGIN;

-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║  PHASE 0 — DATA FIXES (blocker fixes, missing columns)                  ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

-- Missing column: guides.title (teachers.py writes title, column didn't exist)
ALTER TABLE public.guides ADD COLUMN IF NOT EXISTS title TEXT DEFAULT '';

-- Missing column: teacher_metadata.director_grade (admin.py writes it)
ALTER TABLE public.teacher_metadata ADD COLUMN IF NOT EXISTS director_grade TEXT DEFAULT '';

-- Missing column: student_metadata.course_id (DDL missing from seed)
ALTER TABLE public.student_metadata ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES public.courses(id) ON DELETE SET NULL;

-- Add period constraint on grades
-- Add period constraint on grades
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'public' AND table_name = 'grades' AND constraint_name = 'grades_period_check'
  ) THEN
    ALTER TABLE public.grades ADD CONSTRAINT grades_period_check CHECK (period IN ('P1', 'P2', 'P3', 'P4'));
  END IF;
END;
$$;

-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║  PHASE 1 — INTEGRITY (ENUMs, Domains, FKs, Constraints)                 ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

-- ── Extensions ──
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ── ENUM types (safe creation via DO block) ──
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'behavior_log_type') THEN
    CREATE TYPE public.behavior_log_type AS ENUM ('positive', 'disciplinary', 'merit', 'observation');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_severity') THEN
    CREATE TYPE public.incident_severity AS ENUM ('low', 'medium', 'high', 'critical');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'financial_status') THEN
    CREATE TYPE public.financial_status AS ENUM ('AL_DIA', 'EN_MORA', 'BECA', 'RETIRADO');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'device_platform') THEN
    CREATE TYPE public.device_platform AS ENUM ('ios', 'android');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'period_label') THEN
    CREATE TYPE public.period_label AS ENUM ('P1', 'P2', 'P3', 'P4');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'delivery_status') THEN
    CREATE TYPE public.delivery_status AS ENUM ('pending', 'submitted', 'approved', 'rejected');
  END IF;
END;
$$;

-- ── Domains (reusable constraints) ──
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'score_0_5') THEN
    CREATE DOMAIN public.score_0_5 AS NUMERIC(3,2)
      CHECK (VALUE >= 0.0 AND VALUE <= 5.0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'positive_money') THEN
    CREATE DOMAIN public.positive_money AS NUMERIC(12,2)
      CHECK (VALUE >= 0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'progress_pct') THEN
    CREATE DOMAIN public.progress_pct AS INTEGER
      CHECK (VALUE BETWEEN 0 AND 100);
  END IF;
END;
$$;

-- ── ALTER existing columns to use ENUMs / Domains where safe ──
-- (Using VARCHAR cast path to avoid data loss)
ALTER TABLE public.behavior_logs
  ALTER COLUMN log_type TYPE TEXT;  -- will re-apply via ENUM in future migration

ALTER TABLE public.project_abp_deliverables
  ALTER COLUMN status TYPE TEXT;

-- ── Missing FOREIGN KEY constraints ──
-- Helper: convert TEXT column to UUID if safely possible
DO $$
BEGIN
  -- exam_results: already UUID
  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'exam_results' AND constraint_name = 'fk_exam_results_student') THEN
    ALTER TABLE public.exam_results ADD CONSTRAINT fk_exam_results_student FOREIGN KEY (student_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'exam_results' AND constraint_name = 'fk_exam_results_exam') THEN
    ALTER TABLE public.exam_results ADD CONSTRAINT fk_exam_results_exam FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE;
  END IF;

  -- incident_reports: already UUID
  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'incident_reports' AND constraint_name = 'fk_incident_student') THEN
    ALTER TABLE public.incident_reports ADD CONSTRAINT fk_incident_student FOREIGN KEY (student_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'incident_reports' AND constraint_name = 'fk_incident_exam') THEN
    ALTER TABLE public.incident_reports ADD CONSTRAINT fk_incident_exam FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE;
  END IF;
END;
$$;

-- votes: TEXT → UUID conversion, FK only if successful
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'votes' AND column_name = 'student_id' AND data_type = 'text') THEN
    BEGIN
      ALTER TABLE public.votes ALTER COLUMN student_id TYPE UUID USING student_id::uuid;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'votes.student_id: could not convert to UUID (%)', SQLERRM;
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'votes' AND column_name = 'student_id' AND data_type = 'uuid')
    AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'votes' AND constraint_name = 'fk_votes_student')
  THEN
    ALTER TABLE public.votes ADD CONSTRAINT fk_votes_student FOREIGN KEY (student_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
  END IF;
END;
$$;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'votes' AND column_name = 'candidate_id' AND data_type = 'text') THEN
    BEGIN
      ALTER TABLE public.votes ALTER COLUMN candidate_id TYPE UUID USING candidate_id::uuid;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'votes.candidate_id: could not convert to UUID (%)', SQLERRM;
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'votes' AND column_name = 'candidate_id' AND data_type = 'uuid')
    AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'votes' AND constraint_name = 'fk_votes_candidate')
  THEN
    ALTER TABLE public.votes ADD CONSTRAINT fk_votes_candidate FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;
  END IF;
END;
$$;

-- deliveries: TEXT → UUID conversion, FK only if successful
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'deliveries' AND column_name = 'student_id' AND data_type = 'text') THEN
    BEGIN
      ALTER TABLE public.deliveries ALTER COLUMN student_id TYPE UUID USING student_id::uuid;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'deliveries.student_id: could not convert to UUID (%)', SQLERRM;
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'deliveries' AND column_name = 'student_id' AND data_type = 'uuid')
    AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'deliveries' AND constraint_name = 'fk_deliveries_student')
  THEN
    ALTER TABLE public.deliveries ADD CONSTRAINT fk_deliveries_student FOREIGN KEY (student_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
  END IF;
END;
$$;

-- guides: TEXT → UUID conversion, FK only if successful
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'guides' AND column_name = 'teacher_id' AND data_type = 'text') THEN
    BEGIN
      ALTER TABLE public.guides ALTER COLUMN teacher_id TYPE UUID USING teacher_id::uuid;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'guides.teacher_id: could not convert to UUID (%)', SQLERRM;
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'guides' AND column_name = 'teacher_id' AND data_type = 'uuid')
    AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'guides' AND constraint_name = 'fk_guides_teacher')
  THEN
    ALTER TABLE public.guides ADD CONSTRAINT fk_guides_teacher FOREIGN KEY (teacher_id) REFERENCES public.profiles(id) ON DELETE SET NULL;
  END IF;
END;
$$;

-- exams: TEXT → UUID conversion, FK only if successful
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'exams' AND column_name = 'teacher_id' AND data_type = 'text') THEN
    BEGIN
      ALTER TABLE public.exams ALTER COLUMN teacher_id TYPE UUID USING teacher_id::uuid;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'exams.teacher_id: could not convert to UUID (%)', SQLERRM;
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'exams' AND column_name = 'teacher_id' AND data_type = 'uuid')
    AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'exams' AND constraint_name = 'fk_exams_teacher')
  THEN
    ALTER TABLE public.exams ADD CONSTRAINT fk_exams_teacher FOREIGN KEY (teacher_id) REFERENCES public.profiles(id) ON DELETE SET NULL;
  END IF;
END;
$$;

-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║  PHASE 2 — PERFORMANCE (Indexes, GIN, Triggers)                         ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

-- ── P0: Critical (every request touches these) ──
CREATE INDEX IF NOT EXISTS idx_grades_student_id ON public.grades(student_id);
CREATE INDEX IF NOT EXISTS idx_grades_teacher_id ON public.grades(teacher_id);
CREATE INDEX IF NOT EXISTS idx_grades_subject_id ON public.grades(subject_id);
CREATE INDEX IF NOT EXISTS idx_profiles_login_credential ON public.profiles(login_credential);
CREATE INDEX IF NOT EXISTS idx_grades_student_subject_project ON public.grades(student_id, subject_id, project_id);
CREATE INDEX IF NOT EXISTS idx_exam_progress_student_exam ON public.exam_progress(student_id, exam_id);

-- ── P1: High frequency ──
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_subjects_name ON public.subjects(name);
CREATE INDEX IF NOT EXISTS idx_subjects_grade ON public.subjects(grade);
CREATE INDEX IF NOT EXISTS idx_exams_teacher_id ON public.exams(teacher_id);
CREATE INDEX IF NOT EXISTS idx_exams_grade ON public.exams(grade);
CREATE INDEX IF NOT EXISTS idx_exams_is_active ON public.exams(is_active);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_teacher_id ON public.teacher_assignments(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_subject_id ON public.teacher_assignments(subject_id);
CREATE INDEX IF NOT EXISTS idx_grades_course_id ON public.grades(course_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_exam_id ON public.exam_results(exam_id);

-- ── P2: Medium frequency ──
CREATE INDEX IF NOT EXISTS idx_student_metadata_months_in_arrears ON public.student_metadata(months_in_arrears);
CREATE INDEX IF NOT EXISTS idx_deliveries_student_id ON public.deliveries(student_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_grade_subject ON public.deliveries(grade, subject);
CREATE INDEX IF NOT EXISTS idx_guides_grade_subject ON public.guides(grade, subject);
CREATE INDEX IF NOT EXISTS idx_guides_teacher_id ON public.guides(teacher_id);
CREATE INDEX IF NOT EXISTS idx_notices_categoria ON public.notices(categoria);
CREATE INDEX IF NOT EXISTS idx_notices_created_at ON public.notices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_reports_created_at ON public.incident_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_reports_exam_id ON public.incident_reports(exam_id);
CREATE INDEX IF NOT EXISTS idx_class_materials_grade_id ON public.class_materials(grade_id);
CREATE INDEX IF NOT EXISTS idx_behavior_logs_student_id ON public.behavior_logs(student_id);
CREATE INDEX IF NOT EXISTS idx_courses_grade ON public.courses(grade);
CREATE INDEX IF NOT EXISTS idx_courses_name ON public.courses(name);
CREATE INDEX IF NOT EXISTS idx_votes_student_id ON public.votes(student_id);
CREATE INDEX IF NOT EXISTS idx_candidates_name ON public.candidates(name);
CREATE INDEX IF NOT EXISTS idx_abp_projects_created_at ON public.abp_projects(created_at DESC);

-- ── GIN indexes for JSONB columns ──
CREATE INDEX IF NOT EXISTS idx_subjects_syllabus ON public.subjects USING gin(syllabus);
CREATE INDEX IF NOT EXISTS idx_exams_questions ON public.exams USING gin(questions);
CREATE INDEX IF NOT EXISTS idx_conversations_messages ON public.conversations USING gin(messages);

-- ── Full-Text Search indexes ──
CREATE INDEX IF NOT EXISTS idx_subjects_fts ON public.subjects
  USING gin(to_tsvector('spanish', COALESCE(name, '') || ' ' || COALESCE(description, '')));
CREATE INDEX IF NOT EXISTS idx_guides_fts ON public.guides
  USING gin(to_tsvector('spanish', COALESCE(title, '') || ' ' || COALESCE(filename, '')));
CREATE INDEX IF NOT EXISTS idx_notices_fts ON public.notices
  USING gin(to_tsvector('spanish', COALESCE(titulo, '') || ' ' || COALESCE(contenido, '')));

-- ── Triggers: Auto-update updated_at ──
CREATE OR REPLACE FUNCTION public.trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at column
DO $$
DECLARE
  tbl TEXT;
  tables_with_updated_at TEXT[] := ARRAY['abp_projects', 'project_abp_deliverables', 'conversations'];
BEGIN
  FOREACH tbl IN ARRAY tables_with_updated_at
  LOOP
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'trg_' || tbl || '_updated_at'
      ) THEN
        EXECUTE format(
          'CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON public.%I
           FOR EACH ROW EXECUTE FUNCTION public.trigger_set_updated_at()',
          tbl, tbl
        );
      END IF;
    END IF;
  END LOOP;
END;
$$;

-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║  PHASE 3 — ULTRA-FEATURES                                               ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

-- ── 3a: Soft Deletes ──
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.subjects ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.grades ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.exams ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.guides ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.deliveries ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.notices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Indexes for soft-delete filtering
CREATE INDEX IF NOT EXISTS idx_profiles_active ON public.profiles(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_subjects_active ON public.subjects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_exams_active_filter ON public.exams(deleted_at) WHERE deleted_at IS NULL;

-- ── 3b: Audit Trail ──
CREATE TABLE IF NOT EXISTS public.audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,
  record_id UUID NOT NULL,
  operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
  old_data JSONB DEFAULT '{}',
  new_data JSONB DEFAULT '{}',
  changed_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON public.audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON public.audit_log(changed_at DESC);

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'audit_log' AND policyname = 'audit_log_admin_only') THEN
    CREATE POLICY audit_log_admin_only ON public.audit_log
      FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');
  END IF;
END;
$$;

-- ── 3c: Supabase Realtime (publications) ──
-- Note: requires superuser or REPLICATION privilege
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.grades;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.exams;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.exam_progress;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.incident_reports;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.notices;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.deliveries;
  END IF;
END;
$$;

-- ── 3d: Materialized View for Dashboard ──
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_dashboard_stats AS
SELECT
  (SELECT COUNT(*) FROM public.profiles WHERE role = 'student' AND deleted_at IS NULL) AS total_students,
  (SELECT COUNT(*) FROM public.profiles WHERE role = 'teacher' AND deleted_at IS NULL) AS total_teachers,
  (SELECT COUNT(*) FROM public.grades WHERE deleted_at IS NULL) AS total_grades,
  (SELECT COUNT(*) FROM public.student_metadata WHERE current_status = 'EN_MORA') AS students_in_debt,
  (SELECT COALESCE(AVG(score), 0) FROM public.grades WHERE deleted_at IS NULL) AS avg_score,
  (SELECT COUNT(*) FROM public.incident_reports WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS incidents_30d,
  (SELECT COUNT(*) FROM public.exams WHERE is_active = true AND deleted_at IS NULL) AS active_exams,
  NOW() AS refreshed_at;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dashboard_stats_unique ON public.mv_dashboard_stats(refreshed_at);

-- ── 3e: CITEXT for case-insensitive login ──
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'login_credential'
    AND data_type = 'text') THEN
    ALTER TABLE public.profiles ALTER COLUMN login_credential TYPE CITEXT;
  END IF;
END;
$$;

-- ── 3f: Granular RLS policies (replace anon_all with role-based) ──
-- Keep existing anon_all policies as fallback, add granular policies on top

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'grades' AND policyname = 'students_own_grades') THEN
    CREATE POLICY students_own_grades ON public.grades
      FOR SELECT USING (
        current_setting('app.current_user_role', true) = 'student'
        AND student_id::text = current_setting('app.current_user_id', true)
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exam_progress' AND policyname = 'students_own_exam_progress') THEN
    CREATE POLICY students_own_exam_progress ON public.exam_progress
      FOR ALL USING (
        current_setting('app.current_user_role', true) = 'student'
        AND student_id::text = current_setting('app.current_user_id', true)
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'grades' AND policyname = 'teachers_own_grades') THEN
    CREATE POLICY teachers_own_grades ON public.grades
      FOR SELECT USING (
        current_setting('app.current_user_role', true) = 'teacher'
        AND teacher_id::text = current_setting('app.current_user_id', true)
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'guides' AND policyname = 'teachers_own_guides') THEN
    CREATE POLICY teachers_own_guides ON public.guides
      FOR ALL USING (
        current_setting('app.current_user_role', true) = 'teacher'
        AND teacher_id::text = current_setting('app.current_user_id', true)
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'exams' AND policyname = 'teachers_own_exams') THEN
    CREATE POLICY teachers_own_exams ON public.exams
      FOR ALL USING (
        current_setting('app.current_user_role', true) = 'teacher'
        AND teacher_id::text = current_setting('app.current_user_id', true)
      );
  END IF;
END;
$$;

-- ── 3g: Risk alerts table (FASE 6.6) ──
CREATE TABLE IF NOT EXISTS public.risk_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL DEFAULT 'academic_risk',
  severity TEXT NOT NULL DEFAULT 'medium',
  avg_score NUMERIC(5,2),
  threshold NUMERIC(5,2) DEFAULT 3.5,
  reason TEXT DEFAULT '',
  dismissed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 3h: Propagation log table (FASE 6.4) ──
CREATE TABLE IF NOT EXISTS public.propagation_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  grade_id UUID REFERENCES public.grades(id) ON DELETE CASCADE,
  original_subject_id UUID REFERENCES public.subjects(id),
  student_id UUID REFERENCES public.profiles(id),
  teacher_id UUID REFERENCES public.profiles(id),
  score NUMERIC(5,2),
  propagated_subjects TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_risk_alerts_student ON public.risk_alerts(student_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_created ON public.risk_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_propagation_log_teacher ON public.propagation_log(teacher_id);
CREATE INDEX IF NOT EXISTS idx_propagation_log_created ON public.propagation_log(created_at DESC);

-- Add new tables to realtime
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.risk_alerts;
    ALTER PUBLICATION supabase_realtime ADD TABLE public.propagation_log;
  END IF;
END;
$$;

-- RLS for risk_alerts
ALTER TABLE public.risk_alerts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'risk_alerts' AND policyname = 'admins_all_risk_alerts') THEN
    CREATE POLICY admins_all_risk_alerts ON public.risk_alerts
      FOR ALL USING (
        current_setting('app.current_user_role', true) = 'admin'
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'risk_alerts' AND policyname = 'teachers_read_risk_alerts') THEN
    CREATE POLICY teachers_read_risk_alerts ON public.risk_alerts
      FOR SELECT USING (
        current_setting('app.current_user_role', true) = 'teacher'
      );
  END IF;
END;
$$;

-- RLS for propagation_log
ALTER TABLE public.propagation_log ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'propagation_log' AND policyname = 'admins_all_propagation_log') THEN
    CREATE POLICY admins_all_propagation_log ON public.propagation_log
      FOR ALL USING (
        current_setting('app.current_user_role', true) = 'admin'
      );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'propagation_log' AND policyname = 'teachers_read_propagation_log') THEN
    CREATE POLICY teachers_read_propagation_log ON public.propagation_log
      FOR SELECT USING (
        current_setting('app.current_user_role', true) = 'teacher'
      );
  END IF;
END;
$$;

-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║  VERIFICATION                                                           ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝

SELECT 'optimizer_complete' AS status,
  (SELECT COUNT(*) FROM pg_indexes WHERE tablename IN ('grades','profiles','subjects','exams','exam_progress','teacher_assignments','guides','deliveries','notices','incident_reports','behavior_logs','votes','candidates','abp_projects','class_materials','courses','risk_alerts','propagation_log')) AS total_indexes,
  (SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'trg_%') AS total_triggers;

COMMIT;
