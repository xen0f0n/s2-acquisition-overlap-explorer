import type { AcquisitionMode, GeoJsonFeatureCollection, OverlapRequest, PlansResponse, Platform, RefreshResponse } from '../types/domain'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function getPlans(): Promise<PlansResponse> {
  return request<PlansResponse>('/api/plans')
}

export async function refreshPlans(platforms: Platform[]): Promise<RefreshResponse> {
  return request<RefreshResponse>('/api/refresh', {
    method: 'POST',
    body: JSON.stringify({ platforms, max_files_per_platform: 1 }),
  })
}

export async function getAcquisitions(params: {
  platforms: Platform[]
  modes: AcquisitionMode[]
  start?: string | null
  end?: string | null
}): Promise<GeoJsonFeatureCollection> {
  const query = new URLSearchParams()
  query.set('satellites', params.platforms.join(','))
  query.set('modes', params.modes.join(','))
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)
  return request<GeoJsonFeatureCollection>(`/api/acquisitions?${query.toString()}`)
}

export async function getOverlaps(payload: OverlapRequest): Promise<GeoJsonFeatureCollection> {
  return request<GeoJsonFeatureCollection>('/api/overlaps', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
