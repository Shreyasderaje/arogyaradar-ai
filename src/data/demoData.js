// All values in this file are synthetic examples for the hackathon demo.
export const districts = [
  { id: 'bengaluru-urban', name: 'Bengaluru Urban', coverage: 'PARTIAL', demoInputs: { weather: 62, health: 58, vulnerability: 72, services: 68 } },
  { id: 'mysuru', name: 'Mysuru', coverage: 'FULL', demoInputs: { weather: 48, health: 54, vulnerability: 46, services: 74 } },
  { id: 'dakshina-kannada', name: 'Dakshina Kannada', coverage: 'SIGNALS ONLY', demoInputs: { weather: 77, health: 49, vulnerability: 53, services: 61 } },
  { id: 'kalaburagi', name: 'Kalaburagi', coverage: 'PARTIAL', demoInputs: { weather: 68, health: 72, vulnerability: 79, services: 43 } },
  { id: 'belagavi', name: 'Belagavi', coverage: 'FULL', demoInputs: { weather: 56, health: 63, vulnerability: 58, services: 66 } },
]

export const healthTrend = [
  { month: 'Jan', value: 38 }, { month: 'Feb', value: 42 }, { month: 'Mar', value: 39 },
  { month: 'Apr', value: 48 }, { month: 'May', value: 45 }, { month: 'Jun', value: 54 },
  { month: 'Jul', value: 61 }, { month: 'Aug', value: 56 }, { month: 'Sep', value: 67 },
  { month: 'Oct', value: 59 }, { month: 'Nov', value: 65 }, { month: 'Dec', value: 72 },
]

export const initialWeights = { weather: 35, health: 25, vulnerability: 20, services: 20 }
export const resourceDefaults = { beds: 120, rdk: 340, platelets: 85 }
