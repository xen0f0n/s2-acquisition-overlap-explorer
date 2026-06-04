import type { Filters } from '../types/domain'

export const DELTA_STEPS_MINUTES = [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440]

export const DEFAULT_FILTERS: Filters = {
  platforms: ['S2A', 'S2B', 'S2C'],
  modes: ['Nominal'],
  startDate: '',
  endDate: '',
  deltaMinutes: 60,
  requireSpatialIntersection: true,
  minAreaKm2: 0,
  matchKind: 'pairwise',
  mapDisplayMode: 'matches_only',
}

export function minutesLabel(value: number): string {
  if (value < 60) return `${value} min`
  if (value % 60 === 0) return `${value / 60} h`
  return `${(value / 60).toFixed(1)} h`
}

export function dateInputToUtcIso(date: string, endOfDay = false): string | null {
  if (!date) return null
  return `${date}T${endOfDay ? '23:59:59' : '00:00:00'}Z`
}
