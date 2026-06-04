interface Props {
  feature?: GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>> | null
  onClose: () => void
}

const LABELS: Record<string, string> = {
  match_id: 'Match ID',
  platform_a: 'Platform A',
  platform_b: 'Platform B',
  platform_c: 'Platform C',
  acquisition_id_a: 'Acquisition A',
  acquisition_id_b: 'Acquisition B',
  acquisition_id_c: 'Acquisition C',
  start_time_a: 'Start A',
  start_time_b: 'Start B',
  start_time_c: 'Start C',
  stop_time_a: 'Stop A',
  stop_time_b: 'Stop B',
  stop_time_c: 'Stop C',
  time_delta_minutes: 'Time delta minutes',
  time_span_minutes: 'Triple time span minutes',
  delta_ab_minutes: 'Delta A-B minutes',
  delta_ac_minutes: 'Delta A-C minutes',
  delta_bc_minutes: 'Delta B-C minutes',
  intersection_area_km2: 'Intersection area km²',
  mode_a: 'Mode A',
  mode_b: 'Mode B',
  mode_c: 'Mode C',
  source_kml_a: 'Source KML A',
  source_kml_b: 'Source KML B',
  source_kml_c: 'Source KML C',
}

export function MetadataPanel({ feature, onClose }: Props) {
  if (!feature) return null
  const p = feature.properties ?? {}
  const keys = Object.keys(LABELS).filter((key) => p[key] !== undefined && p[key] !== null)

  return (
    <aside className="metadata-panel">
      <div className="metadata-header">
        <h2>Selected match</h2>
        <button onClick={onClose}>×</button>
      </div>
      <dl>
        {keys.map((key) => (
          <div key={key}>
            <dt>{LABELS[key]}</dt>
            <dd>{String(typeof p[key] === 'number' ? Number(p[key]).toLocaleString(undefined, { maximumFractionDigits: 3 }) : p[key])}</dd>
          </div>
        ))}
      </dl>
    </aside>
  )
}
