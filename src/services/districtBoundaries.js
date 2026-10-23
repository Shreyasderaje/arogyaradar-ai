export const DISTRICT_BOUNDARY_PATH = '/data/karnataka-districts.geojson'

const DISTRICT_NAME_ALIASES = {
  bangalore: 'bengaluru-urban',
  'bangalore-urban': 'bengaluru-urban',
  'bangalore-rural': 'bengaluru-rural',
  chamrajnagar: 'chamarajanagara',
  chikmagalur: 'chikkamagaluru',
  belgaum: 'belagavi',
  gulbarga: 'kalaburagi',
  mysore: 'mysuru',
  shimoga: 'shivamogga',
  tumkur: 'tumakuru',
  bijapur: 'vijayapura',
}

function normalize(value) {
  return String(value ?? '').trim().toLocaleLowerCase().replace(/[\s_]+/g, '-').replace(/-+/g, '-')
}

export function matchFeatureToDistrict(feature, districts) {
  const properties = feature?.properties ?? {}
  const featureId = normalize(properties.district_id)
  const featureName = normalize(properties.district_name ?? properties.DISTRICT)

  return districts.find((district) => normalize(district.id) === featureId)
    ?? districts.find((district) => normalize(district.name) === featureName)
    ?? districts.find((district) => normalize(district.id) === DISTRICT_NAME_ALIASES[featureName])
    ?? null
}

function validPosition(position) {
  return Array.isArray(position)
    && position.length >= 2
    && Number.isFinite(position[0])
    && Number.isFinite(position[1])
    && position[0] >= -180 && position[0] <= 180
    && position[1] >= -90 && position[1] <= 90
}

function samePosition(first, last) {
  return first[0] === last[0] && first[1] === last[1]
}

function validRing(ring) {
  return Array.isArray(ring)
    && ring.length >= 4
    && ring.every(validPosition)
    && samePosition(ring[0], ring[ring.length - 1])
}

function validPolygon(polygon) {
  return Array.isArray(polygon) && polygon.length > 0 && polygon.every(validRing)
}

function validGeometry(geometry) {
  if (geometry.type === 'Polygon') return validPolygon(geometry.coordinates)
  return Array.isArray(geometry.coordinates)
    && geometry.coordinates.length > 0
    && geometry.coordinates.every(validPolygon)
}

export function validateDistrictGeoJson(data, districts) {
  if (!data || data.type !== 'FeatureCollection' || !Array.isArray(data.features) || data.features.length === 0) {
    throw new Error('Expected a non-empty GeoJSON FeatureCollection.')
  }

  let matchedFeatures = 0
  for (const feature of data.features) {
    const properties = feature?.properties
    const geometry = feature?.geometry
    const hasDistrictKey = typeof properties?.district_id === 'string' && properties.district_id.trim()
      || typeof properties?.district_name === 'string' && properties.district_name.trim()
      || typeof properties?.DISTRICT === 'string' && properties.DISTRICT.trim()

    if (feature?.type !== 'Feature' || !properties || !hasDistrictKey) {
      throw new Error('Each feature must include properties.district_id, properties.district_name, or properties.DISTRICT.')
    }
    if (!geometry || !['Polygon', 'MultiPolygon'].includes(geometry.type) || !validGeometry(geometry)) {
      throw new Error('Each district feature must contain valid Polygon or MultiPolygon coordinates.')
    }
    if (matchFeatureToDistrict(feature, districts)) matchedFeatures += 1
  }

  if (matchedFeatures === 0) {
    throw new Error('No GeoJSON district_id or district_name values match the demo district records.')
  }

  return data
}

export async function loadDistrictBoundaries(districts, signal) {
  const response = await fetch(DISTRICT_BOUNDARY_PATH, {
    signal,
    headers: { Accept: 'application/geo+json, application/json' },
  })

  if (!response.ok) {
    throw new Error(response.status === 404
      ? `Boundary file not found at ${DISTRICT_BOUNDARY_PATH}.`
      : `Boundary file request failed (${response.status}).`)
  }

  let data
  try {
    data = await response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Boundary file is not valid JSON.', { cause: error })
  }

  return validateDistrictGeoJson(data, districts)
}
