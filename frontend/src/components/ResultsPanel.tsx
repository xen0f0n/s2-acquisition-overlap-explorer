import type { GeoJsonFeatureCollection } from '../types/domain'
import { minutesLabel } from '../state/defaults'

interface Props {
  overlaps?: GeoJsonFeatureCollection
  selectedMatchId?: string | null
  onSelect: (feature: GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>>) => void
}

function fmtDate(value?: string): string {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString().replace('T', ' ').replace('.000Z', ' UTC')
}

export function ResultsPanel({ overlaps, selectedMatchId, onSelect }: Props) {
  const features = overlaps?.features ?? []

  return (
    <aside className="results-panel">
      <div className="results-header">
        <h2>Matches</h2>
        <span>{features.length}</span>
      </div>

      {features.length === 0 && (
        <p className="empty-text">No matching acquisitions for the current filters.</p>
      )}

      <div className="results-list">
        {features.slice(0, 250).map((feature, index) => {
          const p = feature.properties ?? {}
          const selected = selectedMatchId === p.match_id
          return (
            <button
              key={p.match_id ?? index}
              className={`result-card ${selected ? 'selected' : ''}`}
              onClick={() => onSelect(feature)}
            >
              <div className="result-title">
                <strong>{p.platform_c ? `${p.platform_a ?? '?'} ↔ ${p.platform_b ?? '?'} ↔ ${p.platform_c}` : `${p.platform_a ?? '?'} ↔ ${p.platform_b ?? '?'}`}</strong>
                <span>Δt {minutesLabel(Math.round(p.time_delta_minutes ?? 0))}</span>
              </div>
              <p>{p.platform_c ? `${fmtDate(p.start_time_a)} / ${fmtDate(p.start_time_b)} / ${fmtDate(p.start_time_c)}` : `${fmtDate(p.start_time_a)} / ${fmtDate(p.start_time_b)}`}</p>
              {p.intersection_area_km2 !== undefined && (
                <p>{Number(p.intersection_area_km2).toLocaleString(undefined, { maximumFractionDigits: 1 })} km²</p>
              )}
              <small>{p.platform_c ? `${p.source_kml_a} · ${p.source_kml_b} · ${p.source_kml_c}` : `${p.source_kml_a} · ${p.source_kml_b}`}</small>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
