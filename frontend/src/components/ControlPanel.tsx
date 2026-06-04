import type { AcquisitionMode, Filters, Platform } from '../types/domain'
import { DELTA_STEPS_MINUTES, minutesLabel } from '../state/defaults'

const PLATFORMS: Platform[] = ['S2A', 'S2B', 'S2C']
const MODES: AcquisitionMode[] = ['Nominal', 'Vicarious', 'Calibration']

interface Props {
  filters: Filters
  onChange: (filters: Filters) => void
  onRefresh: () => void
  refreshPending: boolean
  refreshMessage?: string
  planCount: number
  acquisitionCount: number
  overlapCount: number
}

function toggleArrayValue<T extends string>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

export function ControlPanel({
  filters,
  onChange,
  onRefresh,
  refreshPending,
  refreshMessage,
  planCount,
  acquisitionCount,
  overlapCount,
}: Props) {
  const deltaIndex = Math.max(0, DELTA_STEPS_MINUTES.indexOf(filters.deltaMinutes))

  return (
    <aside className="control-panel">
      <div className="brand-block">
        <p className="eyebrow">Sentinel-2</p>
        <h1>Acquisition overlap explorer</h1>
        <p className="muted">Planned swath footprints from Copernicus KML acquisition plans.</p>
      </div>

      <section className="panel-section">
        <button className="primary-button" onClick={onRefresh} disabled={refreshPending}>
          {refreshPending ? 'Refreshing…' : 'Refresh latest plans'}
        </button>
        {refreshMessage && <p className="status-text">{refreshMessage}</p>}
        <div className="stats-grid">
          <div><strong>{planCount}</strong><span>plans</span></div>
          <div><strong>{acquisitionCount}</strong><span>footprints</span></div>
          <div><strong>{overlapCount}</strong><span>matches</span></div>
        </div>
      </section>


      <section className="panel-section">
        <div className="section-header">
          <h2>Map detail</h2>
        </div>
        <div className="segmented-control" role="group" aria-label="Map detail">
          <button
            className={filters.mapDisplayMode === 'matches_only' ? 'active' : ''}
            onClick={() => onChange({ ...filters, mapDisplayMode: 'matches_only' })}
          >
            Clean
          </button>
          <button
            className={filters.mapDisplayMode === 'matches_context' ? 'active' : ''}
            onClick={() => onChange({ ...filters, mapDisplayMode: 'matches_context' })}
          >
            Context
          </button>
          <button
            className={filters.mapDisplayMode === 'all_footprints' ? 'active' : ''}
            onClick={() => onChange({ ...filters, mapDisplayMode: 'all_footprints' })}
          >
            All
          </button>
        </div>
        <p className="hint-text">
          Clean shows only overlap geometry. Context adds only the source swaths for matched results. All shows every planned footprint.
        </p>
      </section>

      <section className="panel-section">
        <h2>Satellite units</h2>
        <div className="chip-row">
          {PLATFORMS.map((platform) => (
            <button
              key={platform}
              className={`chip ${filters.platforms.includes(platform) ? 'active' : ''}`}
              onClick={() => {
                const platforms = toggleArrayValue(filters.platforms, platform)
                const nextPlatforms = platforms.length ? platforms : filters.platforms
                onChange({
                  ...filters,
                  platforms: nextPlatforms,
                  matchKind: nextPlatforms.length === 3 ? filters.matchKind : 'pairwise',
                })
              }}
            >
              {platform}
            </button>
          ))}
        </div>
      </section>

      <section className="panel-section">
        <h2>Match grouping</h2>
        <div className="radio-list">
          <label>
            <input
              type="radio"
              checked={filters.matchKind === 'pairwise'}
              onChange={() => onChange({ ...filters, matchKind: 'pairwise' })}
            />
            Pairwise matches
          </label>
          <label>
            <input
              type="radio"
              checked={filters.matchKind === 'triple'}
              disabled={filters.platforms.length !== 3}
              onChange={() => onChange({ ...filters, matchKind: 'triple' })}
            />
            All three together
          </label>
        </div>
        {filters.platforms.length !== 3 && filters.matchKind === 'triple' && (
          <p className="status-text">Triple matching requires S2A, S2B and S2C selected.</p>
        )}
      </section>

      <section className="panel-section">
        <h2>Acquisition mode</h2>
        <div className="checkbox-list">
          {MODES.map((mode) => (
            <label key={mode}>
              <input
                type="checkbox"
                checked={filters.modes.includes(mode)}
                onChange={() => {
                  const modes = toggleArrayValue(filters.modes, mode)
                  onChange({ ...filters, modes: modes.length ? modes : filters.modes })
                }}
              />
              {mode}
            </label>
          ))}
        </div>
      </section>

      <section className="panel-section">
        <h2>Date range</h2>
        <label className="field-label">
          Start date
          <input
            type="date"
            value={filters.startDate}
            onChange={(event) => onChange({ ...filters, startDate: event.target.value })}
          />
        </label>
        <label className="field-label">
          End date
          <input
            type="date"
            value={filters.endDate}
            onChange={(event) => onChange({ ...filters, endDate: event.target.value })}
          />
        </label>
      </section>

      <section className="panel-section">
        <div className="section-header">
          <h2>Time difference</h2>
          <strong>{minutesLabel(filters.deltaMinutes)}</strong>
        </div>
        <input
          type="range"
          min={0}
          max={DELTA_STEPS_MINUTES.length - 1}
          step={1}
          value={deltaIndex}
          onChange={(event) => {
            const next = DELTA_STEPS_MINUTES[Number(event.target.value)]
            onChange({ ...filters, deltaMinutes: next })
          }}
        />
        <div className="range-labels"><span>5 min</span><span>24 h</span></div>
      </section>

      <section className="panel-section">
        <h2>Overlap type</h2>
        <div className="radio-list">
          <label>
            <input
              type="radio"
              checked={filters.requireSpatialIntersection}
              onChange={() => onChange({ ...filters, requireSpatialIntersection: true })}
            />
            Spatial + temporal
          </label>
          <label>
            <input
              type="radio"
              checked={!filters.requireSpatialIntersection}
              onChange={() => onChange({ ...filters, requireSpatialIntersection: false })}
            />
            Temporal only
          </label>
        </div>
      </section>

      <section className="panel-section">
        <h2>Minimum intersection area</h2>
        <label className="field-label">
          km²
          <input
            type="number"
            min={0}
            step={100}
            value={filters.minAreaKm2}
            disabled={!filters.requireSpatialIntersection}
            onChange={(event) => onChange({ ...filters, minAreaKm2: Number(event.target.value) })}
          />
        </label>
      </section>
    </aside>
  )
}
