import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import { GeoJSON, MapContainer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin } from 'lucide-react'
import { calculateDemoScore } from '../services/dashboardService'
import { loadDistrictBoundaries, matchFeatureToDistrict } from '../services/districtBoundaries'

function MapResizer() {
  const map = useMap()

  useEffect(() => {
    const container = map.getContainer()
    const resizeObserver = new ResizeObserver(() => map.invalidateSize({ pan: false }))
    resizeObserver.observe(container)
    map.invalidateSize({ pan: false })
    return () => resizeObserver.disconnect()
  }, [map])

  return null
}

function DistrictPicker({ districts, selectedDistrictId, onSelectDistrict }) {
  return (
    <div className="map-district-list" aria-label="Select a synthetic demo district">
      {districts.map((district) => (
        <button
          key={district.id}
          type="button"
          className={`map-district-option ${selectedDistrictId === district.id ? 'selected' : ''}`}
          aria-pressed={selectedDistrictId === district.id}
          onClick={() => onSelectDistrict(district.id)}
        >
          <span>{district.name}</span>
          <small>{district.coverage ?? 'API LISTED'}</small>
        </button>
      ))}
    </div>
  )
}

function MapPlaceholder({ districts, selectedDistrictId, onSelectDistrict, loading, error }) {
  return (
    <div className="map-placeholder" aria-label="Karnataka district map unavailable">
      <div className="map-grid" aria-hidden="true" />
      <div className="map-state" role={error ? 'status' : undefined} aria-live="polite">
        <div className="map-state-icon"><MapPin size={22} /></div>
        <strong>{loading ? 'Loading Karnataka district boundaries' : 'Karnataka district boundaries unavailable'}</strong>
        <p>{loading
          ? 'Reading the local boundary file. Synthetic district selection remains available.'
          : error || 'Boundary GeoJSON is not connected. Choose a district to update the linked synthetic score.'}</p>
        <span className="map-unavailable-badge">{loading ? 'LOADING LOCAL GEOJSON' : 'BOUNDARIES NOT LOADED'}</span>
        <DistrictPicker districts={districts} selectedDistrictId={selectedDistrictId} onSelectDistrict={onSelectDistrict} />
      </div>
      <div className="map-coords">KARNATAKA · DEMO DISTRICTS</div>
    </div>
  )
}

function buildTooltip(feature, district, score) {
  const content = document.createElement('div')
  const name = document.createElement('strong')
  name.textContent = district?.name ?? feature.properties.district_name ?? feature.properties.DISTRICT ?? feature.properties.district_id
  content.append(name)

  const detail = document.createElement('div')
  detail.textContent = district && score !== null
    ? `Synthetic preparedness score: ${score}/100 · ${district.coverage ?? 'demo profile'}`
    : 'No synthetic demo score available for this district.'
  content.append(detail)
  return content
}

function scoreColor(score) {
  if (score == null) return '#84918a'
  if (score < 50) return '#d49a61'
  if (score < 70) return '#a4ad73'
  return '#4b9968'
}

function DistrictPolygons({ data, districts, selectedDistrictId, weights, onSelectDistrict }) {
  const geoJsonRef = useRef(null)
  const scoreFor = useCallback((district) => district ? calculateDemoScore(district, weights) : null, [weights])

  const styleFeature = useCallback((feature) => {
    const district = matchFeatureToDistrict(feature, districts)
    const score = scoreFor(district)
    const selected = district?.id === selectedDistrictId
    const hasDemoScore = score !== null
    return {
      color: selected ? '#f7fff9' : '#dce9df',
      weight: selected ? 3.5 : 1.6,
      opacity: 0.95,
      fillColor: scoreColor(score),
      fillOpacity: hasDemoScore ? (selected ? 0.88 : 0.7) : (selected ? 0.42 : 0.24),
      dashArray: hasDemoScore ? undefined : '3 4',
    }
  }, [districts, scoreFor, selectedDistrictId])

  const addFeatureInteractions = useCallback((feature, layer) => {
    const district = matchFeatureToDistrict(feature, districts)
    layer.bindTooltip(buildTooltip(feature, district, scoreFor(district)), { sticky: true, direction: 'top', opacity: 0.98, className: 'demo-map-tooltip' })
    layer.on({
      mouseover: (event) => event.target.setStyle({ color: '#ffffff', weight: 3.5, fillOpacity: scoreFor(district) !== null ? 0.94 : 0.48 }),
      mouseout: (event) => geoJsonRef.current?.resetStyle(event.target),
      click: () => { if (district) onSelectDistrict(district.id) },
    })
    if (district) {
      layer.on('add', () => {
        const element = layer.getElement()
        element?.setAttribute('role', 'button')
        element?.setAttribute('tabindex', '0')
        element?.setAttribute('aria-label', `Select ${district.name}${scoreFor(district) === null ? ', no synthetic demo profile' : `, synthetic preparedness score ${scoreFor(district)} out of 100`}`)
      })
      layer.on('keypress', (event) => {
        if (event.originalEvent?.key === 'Enter' || event.originalEvent?.key === ' ') {
          event.originalEvent.preventDefault()
          onSelectDistrict(district.id)
        }
      })
    }
  }, [districts, onSelectDistrict, scoreFor])

  useEffect(() => {
    const layerGroup = geoJsonRef.current
    if (!layerGroup) return
    layerGroup.setStyle(styleFeature)
    layerGroup.eachLayer((layer) => {
      const district = matchFeatureToDistrict(layer.feature, districts)
      layer.setTooltipContent(buildTooltip(layer.feature, district, scoreFor(district)))
      const element = layer.getElement()
      if (element && district) element.setAttribute('aria-label', `Select ${district.name}${scoreFor(district) === null ? ', no synthetic demo profile' : `, synthetic preparedness score ${scoreFor(district)} out of 100`}`)
    })
  }, [districts, scoreFor, selectedDistrictId, styleFeature])

  return <GeoJSON ref={geoJsonRef} data={data} style={styleFeature} onEachFeature={addFeatureInteractions} />
}

function FitMapBounds({ bounds }) {
  const map = useMap()
  useEffect(() => {
    if (bounds?.isValid()) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 8, animate: false })
  }, [bounds, map])
  return <MapResizer />
}

function DistrictMap({ districts, selectedDistrictId, weights, onSelectDistrict }) {
  const [boundaryData, setBoundaryData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    loadDistrictBoundaries(districts, controller.signal)
      .then((data) => {
        setBoundaryData(data)
        setError('')
      })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setBoundaryData(null)
          setError(`${loadError.message} Place a valid file at public/data/karnataka-districts.geojson (served at /data/karnataka-districts.geojson).`)
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [districts])

  const bounds = useMemo(() => boundaryData ? L.geoJSON(boundaryData).getBounds() : null, [boundaryData])

  if (!boundaryData || !bounds?.isValid()) {
    return <MapPlaceholder districts={districts} selectedDistrictId={selectedDistrictId} onSelectDistrict={onSelectDistrict} loading={loading} error={error} />
  }

  return (
    <div className="district-map-view" aria-label="Karnataka district boundaries with synthetic demo scores">
      <MapContainer bounds={bounds} boundsOptions={{ padding: [30, 30], maxZoom: 8 }} scrollWheelZoom zoomControl className="district-leaflet-map">
        <FitMapBounds bounds={bounds} />
        <DistrictPolygons data={boundaryData} districts={districts} selectedDistrictId={selectedDistrictId} weights={weights} onSelectDistrict={onSelectDistrict} />
      </MapContainer>
      <div className="map-data-label">SYNTHETIC DEMO SCORES · ILLUSTRATIVE ONLY</div>
      <div className="map-score-legend" aria-label="Synthetic preparedness score legend">
        <span><i className="score-low" /> &lt; 50</span>
        <span><i className="score-mid" /> 50–69</span>
        <span><i className="score-high" /> 70+</span>
        <span><i className="score-none" /> No demo profile</span>
      </div>
    </div>
  )
}

export default DistrictMap
