export type Platform = 'S2A' | 'S2B' | 'S2C'
export type AcquisitionMode = 'Nominal' | 'Vicarious' | 'Calibration'
export type MatchKind = 'pairwise' | 'triple'
export type MapDisplayMode = 'matches_only' | 'matches_context' | 'all_footprints'

export type GeoJsonFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Geometry, Record<string, any>>

export interface RefreshResponse {
  downloaded_files: number
  parsed_acquisitions: number
  added_acquisitions: number
  plans: Array<Record<string, any>>
}

export interface PlansResponse {
  plans: Array<Record<string, any>>
}

export interface OverlapRequest {
  satellites: Platform[]
  modes: AcquisitionMode[] | null
  start?: string | null
  end?: string | null
  max_time_delta_minutes: number
  require_spatial_intersection: boolean
  min_intersection_area_km2: number
  return_intersection_geometry: boolean
  match_kind: MatchKind
}

export interface Filters {
  platforms: Platform[]
  modes: AcquisitionMode[]
  startDate: string
  endDate: string
  deltaMinutes: number
  requireSpatialIntersection: boolean
  minAreaKm2: number
  matchKind: MatchKind
  mapDisplayMode: MapDisplayMode
}

