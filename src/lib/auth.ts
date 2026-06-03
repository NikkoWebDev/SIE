// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Auth Helpers
// ════════════════════════════════════════════════════════════════

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

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? decodeURIComponent(match[2]) : null
}

export function getToken(): string | null {
  try {
    // Prefer cookie (httpOnly, set by backend)
    const cookieToken = getCookie('access_token')
    if (cookieToken) return cookieToken
    return localStorage.getItem('access_token')
  } catch {
    return null
  }
}

export function getUser(): AuthUser | null {
  try {
    const token = getToken()
    if (!token) return null
    return {
      access_token: token,
      userId: localStorage.getItem('userId') || '',
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
  return !!getToken()
}

export function login(user: AuthUser): void {
  localStorage.setItem('access_token', user.access_token)
  localStorage.setItem('userRole', user.userRole)
  localStorage.setItem('userName', user.userName)
  localStorage.setItem('userId', user.userId)
  if (user.profile_id) localStorage.setItem('profile_id', user.profile_id)
  if (user.userGrade) localStorage.setItem('userGrade', user.userGrade)
  if (user.refresh_token) localStorage.setItem('refresh_token', user.refresh_token)
}

export function logout(): void {
  localStorage.clear()
  // Also clear the httpOnly cookie by pinging the logout endpoint
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
