import { useMemo, useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import 'maplibre-gl/dist/maplibre-gl.css'
import './styles.css'

import { getAcquisitions, getOverlaps, getPlans, refreshPlans } from './api/client'
import { ControlPanel } from './components/ControlPanel'
import { MapView } from './components/MapView'
import { MetadataPanel } from './components/MetadataPanel'
import { ResultsPanel } from './components/ResultsPanel'
import { DEFAULT_FILTERS, dateInputToUtcIso } from './state/defaults'
import type { Filters } from './types/domain'

const queryClient = new QueryClient()

function ExplorerApp() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [selectedFeature, setSelectedFeature] = useState<GeoJSON.Feature<GeoJSON.Geometry, Record<string, any>> | null>(null)
  const [refreshMessage, setRefreshMessage] = useState<string | undefined>()
  const qc = useQueryClient()

  const startIso = useMemo(() => dateInputToUtcIso(filters.startDate, false), [filters.startDate])
  const endIso = useMemo(() => dateInputToUtcIso(filters.endDate, true), [filters.endDate])

  const plansQuery = useQuery({
    queryKey: ['plans'],
    queryFn: getPlans,
  })

  const acquisitionsQuery = useQuery({
    queryKey: ['acquisitions', filters.platforms, filters.modes, startIso, endIso],
    queryFn: () => getAcquisitions({ platforms: filters.platforms, modes: filters.modes, start: startIso, end: endIso }),
    enabled: filters.platforms.length > 0 && filters.modes.length > 0,
  })

  const overlapsQuery = useQuery({
    queryKey: ['overlaps', filters, startIso, endIso],
    queryFn: () => getOverlaps({
      satellites: filters.platforms,
      modes: filters.modes,
      start: startIso,
      end: endIso,
      max_time_delta_minutes: filters.deltaMinutes,
      require_spatial_intersection: filters.requireSpatialIntersection,
      min_intersection_area_km2: filters.minAreaKm2,
      return_intersection_geometry: true,
      match_kind: filters.matchKind,
    }),
    enabled: filters.platforms.length >= (filters.matchKind === 'triple' ? 3 : 2) && filters.modes.length > 0,
  })

  const refreshMutation = useMutation({
    mutationFn: () => refreshPlans(filters.platforms),
    onSuccess: async (data) => {
      setRefreshMessage(`Parsed ${data.parsed_acquisitions} acquisitions; added ${data.added_acquisitions}.`)
      await qc.invalidateQueries({ queryKey: ['plans'] })
      await qc.invalidateQueries({ queryKey: ['acquisitions'] })
      await qc.invalidateQueries({ queryKey: ['overlaps'] })
    },
    onError: (error) => {
      setRefreshMessage(error instanceof Error ? error.message : 'Refresh failed')
    },
  })

  const selectedMatchId = selectedFeature?.properties?.match_id ?? null

  return (
    <div className="app-shell">
      <ControlPanel
        filters={filters}
        onChange={(next) => {
          setFilters(next)
          setSelectedFeature(null)
        }}
        onRefresh={() => refreshMutation.mutate()}
        refreshPending={refreshMutation.isPending}
        refreshMessage={refreshMessage}
        planCount={plansQuery.data?.plans.length ?? 0}
        acquisitionCount={acquisitionsQuery.data?.features.length ?? 0}
        overlapCount={overlapsQuery.data?.features.length ?? 0}
      />

      <main className="main-area">
        {(acquisitionsQuery.isError || overlapsQuery.isError) && (
          <div className="error-banner">
            {String((acquisitionsQuery.error ?? overlapsQuery.error) ?? 'Unknown error')}
          </div>
        )}
        <MapView
          acquisitions={acquisitionsQuery.data}
          overlaps={overlapsQuery.data}
          selectedMatchId={selectedMatchId}
          mapDisplayMode={filters.mapDisplayMode}
          onSelect={setSelectedFeature}
        />
      </main>

      <ResultsPanel
        overlaps={overlapsQuery.data}
        selectedMatchId={selectedMatchId}
        onSelect={setSelectedFeature}
      />

      <MetadataPanel feature={selectedFeature} onClose={() => setSelectedFeature(null)} />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ExplorerApp />
    </QueryClientProvider>
  )
}
