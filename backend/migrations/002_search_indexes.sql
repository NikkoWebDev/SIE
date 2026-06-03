-- Vyntra Academic — Search Indexes Migration
-- Adds full-text search support for AI agent RAG capabilities

-- FTS on class_materials markdown_content (AI-generated educational content)
ALTER TABLE public.class_materials ADD COLUMN IF NOT EXISTS markdown_content TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_class_materials_fts ON public.class_materials
  USING gin(to_tsvector('spanish', COALESCE(markdown_content, '')));

-- FTS on guides content (PDF-extracted text)
ALTER TABLE public.guides ADD COLUMN IF NOT EXISTS content_text TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_guides_content_fts ON public.guides
  USING gin(to_tsvector('spanish', COALESCE(content_text, '')));

-- Helper function for AI agent: search materials and guides by text query
CREATE OR REPLACE FUNCTION public.search_educational_materials(
  search_query TEXT,
  max_results INT DEFAULT 5
)
RETURNS TABLE(
  source_type TEXT,
  title TEXT,
  snippet TEXT,
  url TEXT,
  subject_name TEXT,
  grade TEXT,
  relevance REAL
) AS $$
BEGIN
  RETURN QUERY
  -- Search class_materials
  SELECT
    'material'::TEXT AS source_type,
    cm.file_type AS title,
    COALESCE(LEFT(cm.markdown_content, 200), '') AS snippet,
    cm.file_url AS url,
    COALESCE(s.name, 'Sin materia') AS subject_name,
    cm.grade_id AS grade,
    ts_rank(to_tsvector('spanish', COALESCE(cm.markdown_content, '')), plainto_tsquery('spanish', search_query)) AS relevance
  FROM public.class_materials cm
  LEFT JOIN public.subjects s ON s.id = cm.subject_id
  WHERE to_tsvector('spanish', COALESCE(cm.markdown_content, '')) @@ plainto_tsquery('spanish', search_query)
  UNION ALL
  -- Search guides
  SELECT
    'guide'::TEXT AS source_type,
    COALESCE(g.title, g.filename, 'Guía') AS title,
    COALESCE(LEFT(g.content_text, 200), '') AS snippet,
    g.url AS url,
    g.subject AS subject_name,
    g.grade AS grade,
    ts_rank(to_tsvector('spanish', COALESCE(g.title, '') || ' ' || COALESCE(g.content_text, '')), plainto_tsquery('spanish', search_query)) AS relevance
  FROM public.guides g
  WHERE to_tsvector('spanish', COALESCE(g.title, '') || ' ' || COALESCE(g.content_text, '')) @@ plainto_tsquery('spanish', search_query)
  ORDER BY relevance DESC
  LIMIT max_results;
END;
$$ LANGUAGE plpgsql STABLE;
