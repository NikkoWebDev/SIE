-- Performance Indexes Migration — Vyntra v5.0.1
-- Run: psql $SUPABASE_DB_URL -f migrations/002_performance_indexes.sql

BEGIN;

-- Core query indexes (already covered in 001, reinforcing here)
CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades(student_id);
CREATE INDEX IF NOT EXISTS idx_grades_teacher_id ON grades(teacher_id);
CREATE INDEX IF NOT EXISTS idx_grades_subject_id ON grades(subject_id);
CREATE INDEX IF NOT EXISTS idx_grades_score ON grades(score);
CREATE INDEX IF NOT EXISTS idx_grades_created_at ON grades(created_at DESC);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_grades_lookup ON grades(student_id, subject_id, project_id);
CREATE INDEX IF NOT EXISTS idx_grades_period ON grades(student_id, period);
CREATE INDEX IF NOT EXISTS idx_grades_teacher_subject ON grades(teacher_id, subject_id);

-- Profile indexes
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_login_credential ON profiles(login_credential);
CREATE INDEX IF NOT EXISTS idx_profiles_role_active ON profiles(role, is_active);

-- Student metadata indexes
CREATE INDEX IF NOT EXISTS idx_student_metadata_profile ON student_metadata(profile_id);
CREATE INDEX IF NOT EXISTS idx_student_metadata_status ON student_metadata(current_status);
CREATE INDEX IF NOT EXISTS idx_student_metadata_arrears ON student_metadata(months_in_arrears);

-- Subject indexes
CREATE INDEX IF NOT EXISTS idx_subjects_name ON subjects(name);
CREATE INDEX IF NOT EXISTS idx_subjects_grade ON subjects(grade);
CREATE INDEX IF NOT EXISTS idx_subjects_is_abp ON subjects(is_abp);

-- Teacher assignment indexes
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_teacher ON teacher_assignments(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_subject ON teacher_assignments(subject_id);

-- Exam indexes
CREATE INDEX IF NOT EXISTS idx_exams_teacher ON exams(teacher_id);
CREATE INDEX IF NOT EXISTS idx_exams_grade ON exams(grade);

-- Exam results indexes
CREATE INDEX IF NOT EXISTS idx_exam_results_student ON exam_results(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_score ON exam_results(score);

-- Exam progress indexes
CREATE INDEX IF NOT EXISTS idx_exam_progress_student_exam ON exam_progress(student_id, exam_id);

-- Incident reports indexes
CREATE INDEX IF NOT EXISTS idx_incident_reports_student ON incident_reports(student_id);
CREATE INDEX IF NOT EXISTS idx_incident_reports_exam ON incident_reports(exam_id);
CREATE INDEX IF NOT EXISTS idx_incident_reports_created ON incident_reports(created_at DESC);

-- Notices indexes
CREATE INDEX IF NOT EXISTS idx_notices_categoria ON notices(categoria);
CREATE INDEX IF NOT EXISTS idx_notices_created ON notices(created_at DESC);

-- Candidates / votes indexes
CREATE INDEX IF NOT EXISTS idx_candidates_name ON candidates(name);
CREATE INDEX IF NOT EXISTS idx_votes_student ON votes(student_id);

-- Guides indexes
CREATE INDEX IF NOT EXISTS idx_guides_teacher ON guides(teacher_id);
CREATE INDEX IF NOT EXISTS idx_guides_subject ON guides(subject);

-- Class materials indexes
CREATE INDEX IF NOT EXISTS idx_class_materials_subject ON class_materials(subject_id);
CREATE INDEX IF NOT EXISTS idx_class_materials_grade ON class_materials(grade_id);

-- Conversations indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_role ON conversations(user_id, role);

-- Behavior logs indexes
CREATE INDEX IF NOT EXISTS idx_behavior_logs_student ON behavior_logs(student_id);

-- Risk alerts indexes
CREATE INDEX IF NOT EXISTS idx_risk_alerts_student ON risk_alerts(student_id);

-- Materialized view for dashboard stats (refresh periodically)
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
  (SELECT COUNT(*) FROM profiles WHERE role = 'student') AS total_students,
  (SELECT COUNT(*) FROM profiles WHERE role = 'teacher') AS total_teachers,
  (SELECT COUNT(*) FROM notices) AS total_notices,
  (SELECT COUNT(*) FROM exams) AS total_exams,
  (SELECT COUNT(*) FROM grades) AS total_grades,
  (SELECT COALESCE(AVG(score), 0) FROM grades) AS avg_score,
  (SELECT COUNT(*) FROM student_metadata WHERE months_in_arrears >= 2 AND financial_override = false) AS mora_count;

COMMIT;
