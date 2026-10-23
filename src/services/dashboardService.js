// API integration belongs here when an approved backend contract is available.
// No network calls or backend endpoints are assumed in this demo.
export function calculateDemoScore(district, weights) {
  const weighted = Object.entries(weights).reduce((sum, [key, weight]) => sum + district.demoInputs[key] * Number(weight), 0)
  return Math.round(weighted / 100)
}

export function estimateReadiness(resources) {
  // Illustrative local scenario formula; this is not an operational forecast.
  const score = Math.min(100, Math.round((Math.min(resources.beds / 1.6, 100) + Math.min(resources.rdk / 4.5, 100) + Math.min(resources.platelets / 1.1, 100)) / 3))
  return { score, label: score >= 70 ? 'Well provisioned' : score >= 45 ? 'Moderate coverage' : 'Needs attention' }
}
