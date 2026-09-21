-- Close Supabase Data API access for every current ConceptTree table.
-- The application backend uses its trusted direct database role; public API
-- roles must not read or mutate these tables directly.

BEGIN;

ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.learning_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.deep_learn_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.completion_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_learning_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.learning_session_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.teaching_patterns ENABLE ROW LEVEL SECURITY;

ALTER TABLE IF EXISTS public.users FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.plans FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.edges FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.learning_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.deep_learn_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.notes FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.idempotency_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.completion_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_learning_profile FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.learning_session_records FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.teaching_patterns FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.users FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.user_profiles FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.plans FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.nodes FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.edges FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.learning_sessions FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.deep_learn_sessions FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.notes FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.idempotency_keys FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.completion_notes FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.user_learning_profile FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.learning_session_records FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.teaching_patterns FROM PUBLIC;

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'users', 'user_profiles', 'plans', 'nodes', 'edges',
    'learning_sessions', 'deep_learn_sessions', 'notes', 'idempotency_keys',
    'completion_notes', 'user_learning_profile', 'learning_session_records',
    'teaching_patterns'
  ]
  LOOP
    IF to_regrole('anon') IS NOT NULL THEN
      EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM anon', table_name);
    END IF;
    IF to_regrole('authenticated') IS NOT NULL THEN
      EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM authenticated', table_name);
    END IF;
  END LOOP;
END
$$;

COMMIT;
