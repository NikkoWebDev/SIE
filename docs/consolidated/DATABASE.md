# VYNTRA Academic — Database Schema

## Platform
- **Host**: Supabase (Postgres 15+)
- **Extensions**: `uuid-ossp`, `pg_trgm`, `pg_stat_statements`, `pgcrypto`
- **Client**: `supabase-py` (service_role key for backend operations)

## Key Tables

### profiles
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, default `gen_random_uuid()` |
| login_credential | TEXT | Student/teacher ID (e.g. "ID-000000") |
| fullname | TEXT | Full name |
| password_hash | TEXT | bcrypt hash |
| role | TEXT | "student", "teacher", "admin" |
| is_active | BOOLEAN | Default true |
| email | TEXT | For password recovery + OAuth |
| supabase_auth_id | UUID | Links to Supabase Auth.users |
| created_at | TIMESTAMPTZ | Auto-generated |

### grades
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| student_id | UUID | FK → profiles.id |
| subject_id | UUID | FK → subjects.id |
| teacher_id | UUID | FK → profiles.id |
| score | NUMERIC(3,2) | 0.0 - 5.0 |
| period | TEXT | 'P1','P2','P3','P4' |
| observations | TEXT | |
| created_at | TIMESTAMPTZ | |

### subjects
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Subject name |
| grade | TEXT | Grade level |
| is_abp | BOOLEAN | Is ABP project subject? |
| tutor_ai | TEXT | AI tutor link |
| planner_ai | TEXT | AI planner link |

### class_materials
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| subject_id | UUID | FK → subjects.id |
| grade_id | TEXT | Grade level |
| file_url | TEXT | Google Drive link (original file) |
| file_type | TEXT | "pdf", "docx", "md" |
| markdown_content | TEXT | AI-generated markdown content |
| uploaded_by | UUID | FK → profiles.id |
| created_at | TIMESTAMPTZ | |

### conversations
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | TEXT | profiles.id |
| role | TEXT | "student", "teacher", "admin" |
| messages | JSONB | Array of {role, content} |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### risk_alerts
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| student_id | TEXT | Student identifier |
| score | NUMERIC | Triggering score |
| msg | TEXT | Alert message |
| created_at | TIMESTAMPTZ | |

### propagation_log
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| origin_subject | TEXT | Source subject |
| target_subjects | TEXT[] | Array of propagated subjects |
| grade_id | TEXT | Grade level |
| created_at | TIMESTAMPTZ | |

## RLS Policies
- Tables use `service_role` access (backend manages all queries)
- Anon key has broad access for development
- `profiles` — service_role full access
- `grades` — service_role full access
- `class_materials` — service_role full access

## Seed Data
- Run `backend/seed.sql` in Supabase SQL Editor for initial schema
- Run `backend/migrations/001_schema_optimizer.sql` after seed for optimizations

## Indexes (Performance)
- `profiles(login_credential)` — used for login lookups
- `profiles(supabase_auth_id)` — for OAuth linking
- `grades(student_id)` — grade queries by student
- `grades(teacher_id)` — grade queries by teacher
- `subjects(name)` — subject lookup by name
- `class_materials(subject_id)` — materials per subject
