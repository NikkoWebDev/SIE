import type { AuthUser, UserRole } from './types'

const ROLE_ROUTES: Record<string, string> = {
  ADMIN: '/admin',
  RECTOR: '/admin',
  PROFESOR: '/docente',
  DOCENTE: '/docente',
  ESTUDIANTE: '/estudiante',
  STUDENT: '/estudiante',
  TEACHER: '/docente',
}

export function getToken(): string | null {
  return null // httpOnly cookie — not readable from JS, browser sends it automatically
}

export function getUser(): AuthUser | null {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) return null
    return {
      access_token: '',
      userId,
      profile_id: localStorage.getItem('profile_id') || '',
      userRole: localStorage.getItem('userRole') || '',
      userName: localStorage.getItem('userName') || '',
      userGrade: localStorage.getItem('userGrade') || '',
      is_paid: localStorage.getItem('is_paid') === 'true',
    }
  } catch {
    return null
  }
}

export function getRole(): UserRole | null {
  const role = localStorage.getItem('userRole')?.toUpperCase() || ''
  if (['ADMIN', 'RECTOR'].includes(role)) return 'admin'
  if (['PROFESOR', 'DOCENTE', 'TEACHER'].includes(role)) return 'teacher'
  if (['ESTUDIANTE', 'STUDENT'].includes(role)) return 'student'
  return null
}

export function isAuthenticated(): boolean {
  try {
    return !!localStorage.getItem('userId')
  } catch {
    return false
  }
}

export function login(user: AuthUser): void {
  // Token is stored in httpOnly cookie by backend — not in localStorage
  localStorage.setItem('userRole', user.userRole)
  localStorage.setItem('userName', user.userName)
  localStorage.setItem('userId', user.userId)
  if (user.profile_id) localStorage.setItem('profile_id', user.profile_id)
  if (user.userGrade) localStorage.setItem('userGrade', user.userGrade)
}

export function logout(): void {
  localStorage.clear() // clears ws_access_token too
  const API_URL = (import.meta.env.PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
  fetch(`${API_URL}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {})
  window.location.href = '/'
}

export function redirectToRole(): void {
  const roleRaw = localStorage.getItem('userRole')?.toUpperCase() || ''
  const route = ROLE_ROUTES[roleRaw] || '/dashboard'
  window.location.href = route
}

export function requireAuth(): boolean {
  if (!isAuthenticated()) {
    window.location.href = '/login'
    return false
  }
  return true
}
