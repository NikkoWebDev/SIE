export function metricColor(val: number): string {
  if (val >= 4.0) return 'text-brand-green'
  if (val >= 3.5) return 'text-brand-gold'
  return 'text-brand-danger'
}

export function metricBg(val: number): string {
  if (val >= 4.0) return 'bg-brand-green'
  if (val >= 3.5) return 'bg-brand-gold'
  return 'bg-brand-danger'
}

export function badgeLabel(val: number): string {
  if (val >= 4.0) return 'Sobresaliente'
  if (val >= 3.5) return 'Aceptable'
  return 'En Riesgo'
}

export function ringColor(val: number): string {
  if (val >= 4.0) return '#4caf50'
  if (val >= 3.5) return '#fdc003'
  return '#ba1a1a'
}

export function isCritical(val: number): boolean { return val < 3.5 }

export const CIRCUMFERENCE = 283

export function dashOffset(val: number): number {
  return CIRCUMFERENCE * (1 - val / 5)
}

export type StudentMetric = {
  label: string
  value: number
}

export type Student = {
  id: string
  nombre: string
  grado: string
  jornada: string
  metrics: StudentMetric[]
  promedio: number
  asistencias: number
}
