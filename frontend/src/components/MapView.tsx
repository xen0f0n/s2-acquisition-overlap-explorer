import { useMemo } from 'react'
import DeckGL from '@deck.gl/react'
import { GeoJsonLayer } from '@deck.gl/layers'
import { Map } from 'react-map-gl/maplibre'
import type { PickingInfo } from '@deck.gl/core'
import type { GeoJsonFeatureCollection, MapDisplayMode } from '../types/domain'

interface Props {
  acquisitions?: GeoJsonFeatureCollection
  overlaps?: GeoJsonFeatureCollection
  selectedMatchId?: string | null
  mapDisplayMode: MapDisplayMode
  onSelect: (feature: GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>>) => void
}

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const EMPTY_COLLECTION: GeoJsonFeatureCollection = { type: 'FeatureCollection', features: [] }

function platformLine(platform?: string): [number, number, number, number] {
  if (platform === 'S2A') return [31, 119, 180, 105]
  if (platform === 'S2B') return [255, 127, 14, 105]
  if (platform === 'S2C') return [44, 160, 44, 105]
  return [120, 120, 120, 100]
}

function selectedPlatformLine(platform?: string): [number, number, number, number] {
  if (platform === 'S2A') return [31, 119, 180, 230]
  if (platform === 'S2B') return [255, 127, 14, 230]
  if (platform === 'S2C') return [44, 160, 44, 230]
  return [80, 80, 80, 220]
}

function platformFill(platform?: string): [number, number, number, number] {
  if (platform === 'S2A') return [31, 119, 180, 16]
  if (platform === 'S2B') return [255, 127, 14, 16]
  if (platform === 'S2C') return [44, 160, 44, 16]
  return [120, 120, 120, 14]
}

function formatDelta(p: Record<string, any>): string {
  const value = p.time_span_minutes ?? p.time_delta_minutes
  if (value === undefined || value === null) return 'n/a'
  return `${Number(value).toFixed(1)} min`
}

function involvedAcquisitionIds(overlaps?: GeoJsonFeatureCollection): Set<string> {
  const ids = new Set<string>()

  for (const feature of overlaps?.features ?? []) {
    const p = feature.properties ?? {}
    for (const key of ['acquisition_id_a', 'acquisition_id_b', 'acquisition_id_c']) {
      if (p[key]) ids.add(String(p[key]))
    }
  }

  return ids
}

function selectedAcquisitionIds(overlaps: GeoJsonFeatureCollection | undefined, selectedMatchId?: string | null): Set<string> {
  if (!selectedMatchId) return new Set()

  const feature = overlaps?.features.find((item) => item.properties?.match_id === selectedMatchId)
  if (!feature) return new Set()

  const ids = new Set<string>()
  const p = feature.properties ?? {}
  for (const key of ['acquisition_id_a', 'acquisition_id_b', 'acquisition_id_c']) {
    if (p[key]) ids.add(String(p[key]))
  }
  return ids
}

function filterAcquisitionsByIds(acquisitions: GeoJsonFeatureCollection | undefined, ids: Set<string>): GeoJsonFeatureCollection {
  if (!acquisitions || ids.size === 0) return EMPTY_COLLECTION
  return {
    type: 'FeatureCollection',
    features: acquisitions.features.filter((feature) => ids.has(String(feature.properties?.acquisition_id))),
  }
}

function visibleAcquisitions(
  acquisitions: GeoJsonFeatureCollection | undefined,
  overlaps: GeoJsonFeatureCollection | undefined,
  mode: MapDisplayMode,
): GeoJsonFeatureCollection {
  if (!acquisitions || mode === 'matches_only') return EMPTY_COLLECTION
  if (mode === 'all_footprints') return acquisitions
  return filterAcquisitionsByIds(acquisitions, involvedAcquisitionIds(overlaps))
}

function tooltipHtml(object: any): string {
  const p = object?.properties ?? {}
  if (p.feature_type === 'intersection' || p.feature_type === 'temporal_match' || p.feature_type === 'triple_intersection' || p.feature_type === 'triple_temporal_match') {
    const title = p.platform_c
      ? `${p.platform_a ?? '?'} ↔ ${p.platform_b ?? '?'} ↔ ${p.platform_c}`
      : `${p.platform_a ?? '?'} ↔ ${p.platform_b ?? '?'}`
    const deltaLabel = p.platform_c ? 'span' : 'Δt'
    const cLine = p.platform_c ? `<br/>C: ${p.start_time_c ?? 'n/a'}` : ''
    return `
      <strong>${title}</strong><br/>
      ${deltaLabel}: ${formatDelta(p)}<br/>
      A: ${p.start_time_a ?? 'n/a'}<br/>
      B: ${p.start_time_b ?? 'n/a'}${cLine}<br/>
      Area: ${p.intersection_area_km2 ? Number(p.intersection_area_km2).toFixed(1) : 'n/a'} km²
    `
  }

  return `
    <strong>${p.platform ?? 'Acquisition'}</strong><br/>
    ${p.start_time_utc ?? 'no time'}<br/>
    Mode: ${p.mode ?? 'n/a'}
  `
}

function modeLabel(mode: MapDisplayMode): string {
  if (mode === 'matches_only') return 'Clean view: overlaps only'
  if (mode === 'matches_context') return 'Context view: matched swaths only'
  return 'Debug view: all planned footprints'
}

export function MapView({ acquisitions, overlaps, selectedMatchId, mapDisplayMode, onSelect }: Props) {
  const visibleAcquisitionData = useMemo(
    () => visibleAcquisitions(acquisitions, overlaps, mapDisplayMode),
    [acquisitions, overlaps, mapDisplayMode],
  )

  const selectedAcquisitionData = useMemo(
    () => filterAcquisitionsByIds(acquisitions, selectedAcquisitionIds(overlaps, selectedMatchId)),
    [acquisitions, overlaps, selectedMatchId],
  )

  const acquisitionLayer = new GeoJsonLayer({
    id: 'acquisition-footprints-context',
    data: visibleAcquisitionData,
    pickable: true,
    stroked: true,
    filled: mapDisplayMode === 'all_footprints',
    lineWidthMinPixels: 1,
    getFillColor: (feature: any) => platformFill(feature.properties?.platform),
    getLineColor: (feature: any) => platformLine(feature.properties?.platform),
    onClick: (info: PickingInfo) => {
      if (info.object) onSelect(info.object as GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>>)
    },
  })

  const overlapLayer = new GeoJsonLayer({
    id: 'overlap-footprints-primary',
    data: overlaps ?? EMPTY_COLLECTION,
    pickable: true,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 2,
    getFillColor: (feature: any) => {
      const selected = feature.properties?.match_id === selectedMatchId
      return selected ? [214, 39, 40, 170] : [118, 56, 173, 105]
    },
    getLineColor: (feature: any) => {
      const selected = feature.properties?.match_id === selectedMatchId
      return selected ? [178, 24, 43, 255] : [89, 49, 150, 235]
    },
    getLineWidth: (feature: any) => (feature.properties?.match_id === selectedMatchId ? 4 : 2),
    onClick: (info: PickingInfo) => {
      if (info.object) onSelect(info.object as GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>>)
    },
  })

  const selectedSourceLayer = new GeoJsonLayer({
    id: 'selected-source-swaths',
    data: selectedAcquisitionData,
    pickable: true,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 3,
    getFillColor: (feature: any) => platformFill(feature.properties?.platform),
    getLineColor: (feature: any) => selectedPlatformLine(feature.properties?.platform),
    onClick: (info: PickingInfo) => {
      if (info.object) onSelect(info.object as GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>>)
    },
  })

  return (
    <div className="map-wrapper">
      <DeckGL
        initialViewState={{ longitude: 18, latitude: 42, zoom: 3.2, pitch: 0, bearing: 0 }}
        controller={true}
        layers={[acquisitionLayer, overlapLayer, selectedSourceLayer]}
        getTooltip={({ object }) => object ? { html: tooltipHtml(object), className: 'deck-tooltip' } : null}
      >
        <Map mapStyle={MAP_STYLE} />
      </DeckGL>
      <div className="map-status-pill">{modeLabel(mapDisplayMode)}</div>
      <div className="map-legend">
        <span><i className="legend-s2a" />S2A source swath</span>
        <span><i className="legend-s2b" />S2B source swath</span>
        <span><i className="legend-s2c" />S2C source swath</span>
        <span><i className="legend-overlap" />Overlap</span>
      </div>
    </div>
  )
}
