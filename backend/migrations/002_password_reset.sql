-- VYNTRA Academic — Password Reset + Auth Migration v2.0
-- Run in Supabase SQL Editor after 001_schema_optimizer.sql
BEGIN;

-- Password reset codes table
CREATE TABLE IF NOT EXISTS public.password_reset_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  login_credential TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_codes_profile ON public.password_reset_codes(profile_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_codes_code ON public.password_reset_codes(code);
CREATE INDEX IF NOT EXISTS idx_password_reset_codes_expires ON public.password_reset_codes(expires_at);

-- Enable RLS
ALTER TABLE public.password_reset_codes ENABLE ROW LEVEL SECURITY;

-- Cleanup old codes automatically
CREATE OR REPLACE FUNCTION public.cleanup_expired_reset_codes()
RETURNS TRIGGER AS $$
BEGIN
  DELETE FROM public.password_reset_codes WHERE expires_at < NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE trigger_name = 'trg_cleanup_expired_reset_codes') THEN
    CREATE TRIGGER trg_cleanup_expired_reset_codes
      AFTER INSERT ON public.password_reset_codes
      EXECUTE FUNCTION public.cleanup_expired_reset_codes();
  END IF;
END;
$$;

-- Add GOOGLE_CLIENT_ID column to profiles (for Google OAuth)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS google_client_id TEXT DEFAULT '';

SELECT 'password_reset_migration_complete' AS status;

COMMIT;
