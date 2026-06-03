-- ════════════════════════════════════════════════════════════════
-- VYNTRA Security Hardening Migration
-- ════════════════════════════════════════════════════════════════
-- Run after seed.sql to harden RLS and create security functions

-- 1. Create the secure read-only query function for the AI agent
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

  IF NOT (query_lower ~ '^select ') THEN
    RETURN jsonb_build_object('error', 'Solo se permiten consultas SELECT.');
  END IF;

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

  IF query_lower ~ '\m(drop|truncate|delete|insert|update|alter|create|grant|revoke|exec|execute|call|fetch|copy|declare|raise|notify|listen)\M' THEN
    RETURN jsonb_build_object('error', 'Operación no permitida.');
  END IF;

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

-- 2. Drop permissive RLS policies and create restricted ones
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

-- 3. Create restricted policies
ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS profiles_select ON public.profiles;
CREATE POLICY profiles_select ON public.profiles FOR SELECT
  USING (auth.role() = 'service_role' OR id = auth.uid() OR auth.role() = 'authenticated');

ALTER TABLE IF EXISTS public.student_metadata ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS student_metadata_select ON public.student_metadata;
CREATE POLICY student_metadata_select ON public.student_metadata FOR SELECT
  USING (auth.role() = 'service_role' OR profile_id = auth.uid() OR auth.role() = 'authenticated');

ALTER TABLE IF EXISTS public.grades ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS grades_select ON public.grades;
CREATE POLICY grades_select ON public.grades FOR SELECT
  USING (auth.role() = 'service_role' OR student_id = auth.uid() OR auth.role() = 'authenticated');

-- 4. Password reset codes table (if not exists)
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
