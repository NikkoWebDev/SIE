// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Shared TypeScript Types
// ════════════════════════════════════════════════════════════════

export type UserRole = 'student' | 'teacher' | 'admin'
export type Theme = 'light' | 'dark'
export type Bimester = 'P1' | 'P2' | 'P3' | 'P4'
export type PaymentStatus = 'AL_DIA' | 'EN_MORA'
export type GradeStatus = 'Sobresaliente' | 'Aceptable' | 'En Riesgo'
export type SemesterSubject = 'matematicas' | 'lenguaje' | 'ciencias' | 'sociales' | 'ingles' | 'icfes'

export interface AuthUser {
  access_token: string
  userId: string
  profile_id?: string
  userRole: UserRole | string
  userName: string
  userGrade?: string
  is_paid?: boolean
  refresh_token?: string
}

export interface Profile {
  id: string
  fullname: string
  login_credential: string
  role: UserRole | string
  email?: string
  phone?: string
  shift?: string
  created_at?: string
}

export interface Student extends Profile {
  grade?: string
  is_paid?: boolean
  months_in_arrears?: number
  financial_override?: boolean
  total_balance?: number
  current_status?: PaymentStatus
}

export interface Teacher extends Profile {
  is_director?: boolean
  director_grade?: string
  subjects?: SubjectAssignment[]
}

export interface SubjectAssignment {
  name: string
  grade?: string
}

export interface GradeEntry {
  id?: string
  student_id: string
  subject_id?: string
  subject_name?: string
  score: number
  period?: Bimester
  teacher_id?: string
  student_name?: string
  created_at?: string
}

export interface GradeSheet {
  student_name: string
  subject_name: string
  p1?: number
  p2?: number
  p3?: number
  p4?: number
  average: number
  status: GradeStatus
}

export interface Subject {
  id: string
  name: string
  grade?: string
  is_abp?: boolean
  description?: string
  tutor_ai?: string
  planner_ai?: string
}

export interface Exam {
  id: string
  title: string
  subject_id?: string
  subject_name?: string
  grade?: string
  teacher_id: string
  duration_minutes: number
  questions: ExamQuestion[]
  active?: boolean
  published?: boolean
  created_at?: string
}

export interface ExamQuestion {
  id?: string
  text: string
  options: Record<'A' | 'B' | 'C' | 'D', string>
  correct: 'A' | 'B' | 'C' | 'D'
}

export interface ExamIncident {
  id: string
  student_id: string
  exam_id: string
  student_name?: string
  exam_title?: string
  incident_type: string
  severity: 'low' | 'medium' | 'high'
  strikes: number
  created_at?: string
}

export interface Notice {
  id: string
  titulo?: string
  title?: string
  contenido?: string
  content?: string
  fecha?: string
  date?: string
  categoria?: string
  category?: string
  archivo_url?: string
  resumen?: string
  excerpt?: string
}

export interface Election {
  id: string
  name: string
  photo_url?: string
  votes: number
}

export interface RiskAlert {
  profile_id: string
  fullname: string
  login_credential?: string
  avg_score: number
  status: string
  student_id?: string
  score?: string
  type?: string
  msg?: string
  reason?: string
  severity?: 'low' | 'medium' | 'high'
  created_at?: string
}

export interface ScheduleSlot {
  subject?: string
  materia?: string
  classroom?: string
  aula?: string
  time?: string
  hour?: string
}

export interface Schedule {
  grado?: string
  grade_name?: string
  days?: Record<string, ScheduleSlot[]>
  hours?: { time?: string; hour?: string }[]
  schedule?: Record<string, ScheduleSlot[]>
}

export interface DashboardStats {
  total_students: number
  total_teachers: number
  total_grades?: number
  total_notices?: number
  mora?: number
  en_mora?: number
  al_dia?: number
  average_score?: number
  paid?: number
  unpaid?: number
}

export interface FinancialStatus {
  months_in_arrears: number
  financial_override: boolean
  is_blocked: boolean
  total_balance: number
  current_status: PaymentStatus
}

export interface Homework {
  id: string
  _id?: string
  title: string
  subject_id?: string
  file_url?: string
  comment?: string
  student_name?: string
  subject?: string
  grade?: string
  created_at?: string
}

export interface Guide {
  _id?: string
  id?: string
  title: string
  subject_name?: string
  subject?: string
  grade?: string
  file_url?: string
  teacher_id?: string
  created_at?: string
}

export interface SaberMaterial {
  area: SemesterSubject
  bimestre: number
  title: string
  type: string
  url?: string
}

export interface ApiResponse<T> {
  data: T
  detail?: string
  mensaje?: string
  error?: string
}

export type SectionId =
  | 'inicio'
  | 'notas'
  | 'examenes'
  | 'horarios'
  | 'tareas'
  | 'saber'
  | 'biblioteca'
  | 'votaciones'
  | 'perfil'
  | 'contenidos'
  | 'materiales'
  | 'incidentes'
  | 'alertas'
  | 'estudiantes'
  | 'docentes'
  | 'materias'
  | 'avisos'
  | 'elecciones'
  | 'administradores'
