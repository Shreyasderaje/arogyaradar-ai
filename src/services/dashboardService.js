export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001').replace(/\/$/, '')

async function apiRequest(path, signal, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal,
      headers: { Accept: 'application/json', ...options.headers },
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(`Cannot reach the ArogyaRadar API at ${API_BASE_URL}.`, { cause: error })
  }

  let payload
  try {
    payload = await response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(`The API returned an invalid response for ${path}.`, { cause: error })
  }

  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`
    throw new Error(detail)
  }
  return payload
}

export function getApiHealth(signal) {
  return apiRequest('/api/v1/health', signal)
}

export async function getApiDistricts(signal) {
  const payload = await apiRequest('/api/v1/districts', signal)
  if (!Array.isArray(payload?.districts) || payload.districts.some((district) => !district?.id || !district?.name)) {
    throw new Error('The district endpoint did not return a valid districts list.')
  }
  return payload.districts
}

export function getDistrictWeather(districtId, signal) {
  return apiRequest(`/api/v1/districts/${encodeURIComponent(districtId)}/weather`, signal)
}

export async function getDistrictHistory(districtId, signal) {
  const payload = await apiRequest(`/api/v1/districts/${encodeURIComponent(districtId)}/history`, signal)
  if (!Array.isArray(payload?.records)) {
    throw new Error('The history endpoint did not return a valid records list.')
  }
  return payload
}

export function getDistrictScore(districtId, signal) {
  return apiRequest(`/api/v1/districts/${encodeURIComponent(districtId)}/score`, signal)
}

export function assessDistrictMonth(districtId, currentMonth, signal) {
  if (typeof districtId !== 'string' || !districtId.trim()) {
    throw new Error('Select a district before requesting an assessment.')
  }
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(currentMonth ?? '')) {
    throw new Error('Choose a valid month in YYYY-MM format.')
  }

  return apiRequest('/api/v1/district-month/assess', signal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ district_id: districtId, current_month: currentMonth }),
  })
}

function normalize(value) {
  return String(value ?? '').trim().toLocaleLowerCase().replace(/[\s_]+/g, '-').replace(/-+/g, '-')
}

export function mergeApiDistricts(apiDistricts, demoDistricts) {
  return apiDistricts.map((apiDistrict) => {
    const demoProfile = demoDistricts.find((district) => normalize(district.id) === normalize(apiDistrict.id))
      ?? demoDistricts.find((district) => normalize(district.name) === normalize(apiDistrict.name))

    return {
      ...demoProfile,
      id: apiDistrict.id,
      name: apiDistrict.name,
      coverage: demoProfile?.coverage ?? null,
      demoInputs: demoProfile?.demoInputs ?? null,
      source: 'api',
    }
  })
}

export function calculateDemoScore(district, weights) {
  if (!district?.demoInputs) return null
  const weighted = Object.entries(weights).reduce((sum, [key, weight]) => sum + district.demoInputs[key] * Number(weight), 0)
  return Math.round(weighted / 100)
}

export function estimateReadiness(resources) {
  // Illustrative local scenario formula; this is not an operational forecast.
  const score = Math.min(100, Math.round((Math.min(resources.beds / 1.6, 100) + Math.min(resources.rdk / 4.5, 100) + Math.min(resources.platelets / 1.1, 100)) / 3))
  return { score, label: score >= 70 ? 'Well provisioned' : score >= 45 ? 'Moderate coverage' : 'Needs attention' }
}
