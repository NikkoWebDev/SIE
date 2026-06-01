# VYNTRA Academic — Backend Conventions

## Stack
- **Framework**: FastAPI (title: "Vyntra Core — Academic Platform v5.0.0")
- **Runtime**: Python 3.12+ via Docker on Render
- **Database**: Supabase (Postgres with `supabase-py` client)
- **Auth**: JWT (PyJWT, HS256) with bcrypt password hashing

## Environment Variables (required)
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key (admin access) |
| `SUPABASE_ANON_KEY` | Anon key (public access) |
| `JWT_SECRET` | JWT signing secret |
| `OPENROUTER_STUDENT_KEY` | OpenRouter key for student AI tutor |
| `OPENROUTER_TEACHER_KEY` | OpenRouter key for teacher AI assistant |
| `OPENROUTER_ADMIN_KEY` | OpenRouter key for admin assistant |
| `OPENROUTER_MODEL` | Model name (default: `openrouter/free`) |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name (for MD file storage) |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `GOOGLE_DRIVE_CREDENTIALS_JSON` | Google service account JSON (for Drive upload) |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID for uploads |
| `SENTRY_DSN` | Sentry error tracking |

## Router Structure
All routes in `backend/routers/`:
- `auth.py` — Login, register, OAuth, password recovery
- `admin.py` — Admin CRUD, stats
- `teachers.py` — Grade submission, material upload, guides
- `students.py` — Student data, financial status
- `exams.py` — Exam management, risk alerts
- `grades.py` — Grade queries, PDF generation
- `subjects.py` — Subject listing
- `ai_agent.py` — AI chat with 3 role variants

## AI Agent (`ai_agent.py`)
Three endpoints, each with role-specific system prompt:
- `POST /api/ai/student-tutor` — Empathic tutor for ABP subjects (1024 tokens, 0.7 temp)
- `POST /api/ai/teacher-tutor` — Analytical pedagogical assistant (2048 tokens, 0.6 temp)
- `POST /api/ai/admin-assistant` — Executive advisor (2048 tokens, 0.5 temp)

### ReAct Loop
- Max 5 iterations (tool calls)
- Tools: `get_student_grades_summary`, `get_financial_status`, `get_risk_students`, `get_teacher_grade_count`, `get_subject_info`, `get_subject_materials`, `get_admin_stats`, `get_all_students_financial`
- SSE streaming via `StreamingResponse`
- Conversation persistence: in-memory OrderedDict + Supabase `conversations` table

## Auth Dependencies
- `auth_dependency` — Validates JWT, returns `sub` (user ID)
- `teacher_dependency` — Requires teacher/profesor role
- `admin_dependency` — Requires admin/rector role

## Database
- Client initialized in `config/database.py`
- Migrations in `backend/migrations/001_schema_optimizer.sql`
- Profiles table stores: `id (UUID)`, `login_credential`, `fullname`, `password_hash`, `role`, `is_active`, `email`, `supabase_auth_id`

## Testing
- Pytest in `backend/tests/test_api.py` (5 tests: health, login, validation, notices, risk-alerts auth)
- Run: `cd backend && python -m pytest tests/`

## Upload Flow (Teachers)
1. Teacher uploads PDF/Word to `POST /api/upload-material`
2. Background task: extract text (PyMuPDF/python-docx), send to AI for markdown compression
3. Markdown result → uploaded to Cloudinary (`class_materials` folder)
4. Original file → uploaded to Google Drive via service account
5. Both URLs + markdown content saved to `class_materials` table
6. Progress tracked via `GET /api/upload-material-status/{task_id}` (polling)
