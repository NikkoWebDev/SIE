-- ════════════════════════════════════════════════════════════════
-- VYNTRA Chat History Migration
-- Persists AI Tutor conversations in Supabase (replaces in-memory)
-- ════════════════════════════════════════════════════════════════

-- 1. Create conversations table if not exists
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_conversations_user_role ON conversations (user_id, role);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations (updated_at DESC);

-- 3. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_conversations_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_conversations_updated ON conversations;
CREATE TRIGGER trg_conversations_updated
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_timestamp();

-- 4. TTL cleanup: conversations older than 90 days
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
    DELETE FROM conversations
    WHERE updated_at < now() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. RLS: users can only see their own conversations; admins see all
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS conversations_self ON conversations;
CREATE POLICY conversations_self ON conversations
    FOR ALL
    USING (user_id = auth.uid()::uuid);

DROP POLICY IF EXISTS conversations_admin ON conversations;
CREATE POLICY conversations_admin ON conversations
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM profiles
        WHERE id = auth.uid()::uuid AND role IN ('admin', 'rector')
    ));

-- 6. Grant access
GRANT ALL ON conversations TO authenticated;
GRANT ALL ON conversations TO service_role;
