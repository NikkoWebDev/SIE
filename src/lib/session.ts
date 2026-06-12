// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Unified Session Manager
// httpOnly cookie is the real auth source.
// localStorage only stores UX metadata (name, role, grade).
// ════════════════════════════════════════════════════════════════

import type { UserRole } from './types'

const ROLE_ROUTES: Record<string, string> = {
  ADMIN: '/admin',
  RECTOR: '/admin',
  PROFESOR: '/docente',
  DOCENTE: '/docente',
  ESTUDIANTE: '/estudiante',
  STUDENT: '/estudiante',
  TEACHER: '/docente',
}

export function getUser(): {
  userId: string
  userRole: string
  userName: string
  profile_id: string
  userGrade: string
} | null {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) return null
    return {
      userId,
      profile_id: localStorage.getItem('profile_id') || '',
      userRole: localStorage.getItem('userRole') || '',
      userName: localStorage.getItem('userName') || '',
      userGrade: localStorage.getItem('userGrade') || '',
    }
  } catch { return null }
}

export function getRole(): UserRole | null {
  const role = (localStorage.getItem('userRole') || '').toUpperCase()
  if (['ADMIN', 'RECTOR'].includes(role)) return 'admin'
  if (['PROFESOR', 'DOCENTE', 'TEACHER'].includes(role)) return 'teacher'
  if (['ESTUDIANTE', 'STUDENT'].includes(role)) return 'student'
  return null
}

export function isAuthenticated(): boolean {
  try { return !!localStorage.getItem('userId') } catch { return false }
}

export function clearSession(): void {
  try { localStorage.clear() } catch (_) { /* noop */ }
}

export async function logout(): Promise<void> {
  const API_URL = (import.meta.env.PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
  try {
    await fetch(`${API_URL}/api/auth/logout`, { method: 'POST', credentials: 'include' })
  } catch (_) { /* best effort */ }
  clearSession()
  window.location.href = '/'
}

export function redirectToRole(roleOverride?: string): void {
  const roleRaw = (roleOverride || localStorage.getItem('userRole') || '').toUpperCase()
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

export function storeSession(data: {
  access_token?: string
  rol?: string
  userRole?: string
  nombre?: string
  fullname?: string
  userName?: string
  profile_id?: string
  userId?: string
  userIdFromCred?: string
  grado?: string
  grade?: string
  userGrade?: string
}): void {
  if (data.access_token) {
    // ws_access_token is the ONLY token in localStorage (for WebSocket)
    localStorage.setItem('ws_access_token', data.access_token)
  }
  const role = (data.rol || data.userRole || '').toUpperCase()
  localStorage.setItem('userRole', role)
  localStorage.setItem('userName', data.nombre || data.fullname || data.userName || '')
  localStorage.setItem('userId', data.profile_id || data.userId || data.userIdFromCred || '')
  if (data.profile_id) localStorage.setItem('profile_id', data.profile_id)
  if (data.grado || data.grade) localStorage.setItem('userGrade', data.grado || data.grade || '')
}

// Expose on window for backward compatibility (once)
if (typeof window !== 'undefined' && !window.__sessionExposed) {
  window.__sessionExposed = true
  window.VyntraSession = { getUser, getRole, isAuthenticated, clearSession, logout, redirectToRole, requireAuth, storeSession }
}
