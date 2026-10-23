import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowUpRight, Bell, ChevronDown, CircleHelp, CloudRain, Database, Droplets, HeartPulse, Layers3, MapPin, Menu, Package, Settings2, ShieldCheck, Sparkles, Stethoscope, Wind, X } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { districts, healthTrend, initialWeights, resourceDefaults } from './data/demoData'
import { calculateDemoScore, estimateReadiness, getApiDistricts, getApiHealth, getDistrictHistory, getDistrictScore, getDistrictWeather, mergeApiDistricts } from './services/dashboardService'
import DistrictMap from './components/DistrictMap'
import { DistrictSignalsPage, HealthIndicatorsPage, ResourcePlanningPage } from './components/WorkspacePages'
import './App.css'

const navItems = [
  { label: 'Overview', icon: Layers3 }, { label: 'District signals', icon: MapPin },
  { label: 'Health indicators', icon: HeartPulse }, { label: 'Resource planning', icon: Package },
]
const weights = [
  { key: 'weather', label: 'Weather signals', color: 'mint' },
  { key: 'health', label: 'Historical health signal', color: 'blue' },
  { key: 'vulnerability', label: 'Population vulnerability', color: 'violet' },
  { key: 'services', label: 'Service & infrastructure', color: 'amber' },
]

function Badge({ children, kind = '' }) { return <span className={`badge ${kind}`}>{children}</span> }
function SectionTitle({ eyebrow, title, action }) { return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{action}</div> }

function WeatherSummaryCard({ district, weather, loading, error }) {
  const current = weather?.current
  const isCurrentAvailable = ['live', 'cached'].includes(weather?.data_status) && current
  const format = (value, unit) => Number.isFinite(value) ? `${value}${unit}` : 'Not reported'
  const status = weather?.data_status

  return <article className="summary-card weather-summary-card">
    <div className="summary-top"><span className="summary-icon blue-icon"><CloudRain size={17} /></span><span className="summary-label">WEATHER SIGNAL</span><span className={`soft-tag ${status === 'unavailable' || error ? 'weather-unavailable' : ''}`}>{loading ? 'Loading' : error ? 'API error' : status ?? 'Unavailable'}</span></div>
    <div className="summary-value weather-main-value">{loading ? <span className="weather-value-skeleton" role="status" aria-label={`Loading weather for ${district.name}`} /> : isCurrentAvailable ? format(current.temperature_2m, '°C') : 'Unavailable'}</div>
    <div className="weather-source">{loading ? `Fetching ${district.name}` : isCurrentAvailable ? `${weather.source ?? 'Backend weather'} · ${district.name}` : error ? 'Weather request failed; no reading shown' : weather?.message ?? `No weather reading for ${district.name}`}</div>
    <div className="weather-visual weather-readings">
      <div className="weather-line"><span>Precipitation</span><b>{loading ? 'Loading' : isCurrentAvailable ? format(current.precipitation, ' mm') : 'Unavailable'}</b></div>
      <div className="weather-line"><span>Relative humidity</span><b className="neutral-text">{loading ? 'Loading' : isCurrentAvailable ? format(current.relative_humidity_2m, '%') : 'Unavailable'}</b></div>
      {status === 'cached' && <span className="weather-cache-note">Cached reading · live weather currently unavailable</span>}
      {weather?.data_as_of && <span className="weather-cache-note">Observed {weather.data_as_of}</span>}
    </div>
  </article>
}

function App() {
  const [districtId, setDistrictId] = useState(districts[0].id)
  const [dashboardDistricts, setDashboardDistricts] = useState(districts)
  const [districtListStatus, setDistrictListStatus] = useState('loading')
  const [backendHealth, setBackendHealth] = useState('loading')
  const [districtApiData, setDistrictApiData] = useState(null)
  const [activeNav, setActiveNav] = useState('Overview')
  const [weightsValue, setWeightsValue] = useState(initialWeights)
  const [resources, setResources] = useState(resourceDefaults)
  const [mobileOpen, setMobileOpen] = useState(false)
  const district = dashboardDistricts.find((item) => item.id === districtId) ?? dashboardDistricts[0] ?? districts[0]
  const score = useMemo(() => calculateDemoScore(district, weightsValue), [district, weightsValue])
  const selectedApiData = districtApiData?.districtId === district.id ? districtApiData : null
  const apiScore = selectedApiData?.score
  const weather = selectedApiData?.weather
  const weatherLoading = !selectedApiData
  const readiness = useMemo(() => estimateReadiness(resources), [resources])
  const totalWeight = Object.values(weightsValue).reduce((sum, weight) => sum + Number(weight), 0)
  const availabilityRows = [
    { label: 'Weather', value: !selectedApiData ? 'Loading' : selectedApiData.weatherError ? 'Error' : selectedApiData.weather?.data_status ?? 'Unavailable' },
    { label: 'Health history', value: !selectedApiData ? 'Loading' : selectedApiData.historyError ? 'Error' : selectedApiData.history?.data_status ?? 'Unavailable' },
    { label: 'District score', value: !selectedApiData ? 'Loading' : selectedApiData.scoreError ? 'Error' : selectedApiData.score?.data_status ?? 'Unavailable' },
  ]

  useEffect(() => {
    const controller = new AbortController()
    getApiHealth(controller.signal)
      .then(() => setBackendHealth('connected'))
      .catch((error) => { if (error.name !== 'AbortError') setBackendHealth('unavailable') })
    getApiDistricts(controller.signal)
      .then((apiDistricts) => {
        if (!apiDistricts.length) throw new Error('No supported districts were returned.')
        const mergedDistricts = mergeApiDistricts(apiDistricts, districts)
        setDashboardDistricts(mergedDistricts)
        setDistrictListStatus('connected')
        setDistrictId((currentId) => mergedDistricts.some((item) => item.id === currentId) ? currentId : mergedDistricts[0].id)
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setDashboardDistricts(districts)
          setDistrictListStatus('fallback')
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!district?.id) return undefined
    const controller = new AbortController()
    Promise.allSettled([
      getDistrictWeather(district.id, controller.signal),
      getDistrictScore(district.id, controller.signal),
      getDistrictHistory(district.id, controller.signal),
    ]).then(([weatherResult, scoreResult, historyResult]) => {
      if (controller.signal.aborted) return
      setDistrictApiData({
        districtId: district.id,
        weather: weatherResult.status === 'fulfilled' ? weatherResult.value : null,
        weatherError: weatherResult.status === 'rejected' ? weatherResult.reason.message : null,
        score: scoreResult.status === 'fulfilled' ? scoreResult.value : null,
        scoreError: scoreResult.status === 'rejected' ? scoreResult.reason.message : null,
        history: historyResult.status === 'fulfilled' ? historyResult.value : null,
        historyError: historyResult.status === 'rejected' ? historyResult.reason.message : null,
      })
    })
    return () => controller.abort()
  }, [district?.id])

  const updateWeight = (key, value) => setWeightsValue((current) => {
    const next = { ...current, [key]: Number(value) }
    const others = weights.filter((weight) => weight.key !== key)
    const remaining = 100 - Number(value)
    const otherTotal = others.reduce((sum, weight) => sum + Number(current[weight.key]), 0)
    others.forEach((weight, index) => {
      next[weight.key] = index === others.length - 1 ? remaining - others.slice(0, index).reduce((sum, item) => sum + next[item.key], 0) : Math.round(remaining * current[weight.key] / otherTotal)
    })
    return next
  })
  const updateResource = (key, value) => setResources((current) => ({ ...current, [key]: Math.max(0, Number(value) || 0) }))

  return <div className="app-shell">
    {mobileOpen && <button className="mobile-backdrop" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Activity size={20} strokeWidth={2.5} /></div><div><strong>ArogyaRadar<span>AI</span></strong><small>PUBLIC HEALTH INTELLIGENCE</small></div><button className="close-menu" aria-label="Close menu" onClick={() => setMobileOpen(false)}><X size={18} /></button></div>

      <nav className="nav-list" aria-label="Main navigation">{navItems.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activeNav === label ? 'active' : ''}`} aria-current={activeNav === label ? 'page' : undefined} onClick={() => { setActiveNav(label); setMobileOpen(false) }}><Icon size={17} /><span>{label}</span></button>)}</nav>
      <div className="sidebar-bottom"><div className="coverage-note"><div className="note-icon"><ShieldCheck size={16} /></div><div><strong>Demo workspace — Health figures are synthetic</strong></div></div><button className="nav-item"><Settings2 size={17} /><span>Settings</span></button><button className="nav-item"><CircleHelp size={17} /><span>Help & documentation</span></button><div className="profile"><div className="profile-copy"><strong>Public Health Workspace</strong><small>Demo environment</small></div></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="header-left"><button className="mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumbs"><span>Workspace</span><span className="crumb-sep">/</span><strong>{activeNav}</strong></div></div><div className="header-actions"><span className={`freshness status-${backendHealth}`}><span className={backendHealth === 'connected' ? 'live-dot' : 'live-dot offline'} />{backendHealth === 'connected' ? 'Backend connected' : backendHealth === 'loading' ? 'Connecting to backend…' : 'Backend unavailable'}</span><button className="icon-button notification" aria-label="No new notifications in this demo workspace" title="No new notifications in this demo workspace"><Bell size={17} /></button><div className="user-chip"><span className="avatar small-avatar">AR</span><ChevronDown size={14} /></div></div></header>
      <div className="content">
        <section className={`page-intro ${activeNav !== 'Overview' ? 'subpage-intro' : ''}`}><div>{activeNav === 'Overview' && <><h1>Karnataka Public Health Overview</h1><p>District-level health signals, weather conditions, and resource readiness.</p></>}</div><label className="district-select-wrap"><span>Selected district · {districtListStatus === 'connected' ? 'Backend' : districtListStatus === 'loading' ? 'Loading list' : 'Local fallback'}</span><div className="select-control"><MapPin size={16} /><select aria-label="Selected district" value={districtId} onChange={(event) => setDistrictId(event.target.value)}>{dashboardDistricts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><ChevronDown size={15} className="select-chevron" /></div></label></section>
        <div className="demo-banner"><span className="demo-banner-icon"><Sparkles size={15} /></span><div><strong>SYNTHETIC DEMO DATA</strong><span> Local health profiles, trend, and scores are illustrative. Backend values retain their reported status.</span></div><button aria-label="About demo data" title="Health profiles, trend points, and local scores are synthetic. Backend values retain their reported status and source."><CircleHelp size={15} /></button></div>

        {activeNav === 'Overview' ? <>
        <section className="summary-grid" aria-label="Dashboard summary">
          <article className="summary-card"><div className="summary-top"><span className="summary-icon blue-icon"><CircleHelp size={17} /></span><span className="summary-label">DISTRICTS TO REVIEW</span><span className="soft-tag">DEMO</span></div><div className="summary-value summary-value-text">Unavailable</div><div className="summary-foot"><span>No validated review count returned by the API</span><button className="inline-link" type="button" aria-label="View districts in District Signals" onClick={() => setActiveNav('District signals')}>View districts <ArrowUpRight size={12} /></button></div></article>
          <WeatherSummaryCard district={district} weather={weather} loading={weatherLoading} error={selectedApiData?.weatherError} />
          <article className="summary-card availability-card"><div className="summary-top"><span className="summary-icon mint-icon"><Database size={17} /></span><span className="summary-label">SELECTED-DISTRICT DATA</span><span className="soft-tag">API STATUS</span></div><div className="availability-list">{availabilityRows.map(({ label, value }) => <div className="availability-row" key={label}><span>{label}</span><span className={`availability-status ${value === 'Loading' ? 'loading' : value === 'Error' ? 'error' : value === 'Unavailable' ? 'unavailable' : 'reported'}`}>{value.replaceAll('_', ' ')}</span></div>)}</div></article>
        </section>

        <section className="primary-grid">
          <article className="panel map-panel"><SectionTitle title="Karnataka district map" action={<span className="map-instruction">Select a boundary or use the district selector</span>} /><DistrictMap districts={dashboardDistricts} selectedDistrictId={districtId} weights={weightsValue} onSelectDistrict={setDistrictId} /><div className="map-foot"><div className="selected-place" aria-live="polite"><span className="place-pin"><MapPin size={14} /></span><span><strong>{district.name}</strong><small>Selected district · {district.demoInputs ? 'Synthetic demo profile' : 'No local demo profile'}</small></span></div>{district.coverage ? <Badge kind={district.coverage.toLowerCase().replace(' ', '-')}>{district.coverage}</Badge> : <Badge kind="signals">NO DEMO PROFILE</Badge>}</div></article>
          <article className="panel trend-panel"><SectionTitle title="Monthly indicator trend" action={<span className="chart-period">12 MONTHS</span>} /><div className="chart-subtitle"><span className="chart-legend" /> Composite demo indicator <span className="chart-units">INDEX · ILLUSTRATIVE</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={healthTrend} margin={{ top: 12, right: 5, left: -5, bottom: 0 }}><defs><linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4fba9b" stopOpacity={0.2} /><stop offset="100%" stopColor="#4fba9b" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#2b3c32" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#a9b9ad', fontSize: 12 }} dy={10} /><YAxis domain={[20, 80]} axisLine={false} tickLine={false} tick={{ fill: '#a9b9ad', fontSize: 12 }} ticks={[20, 40, 60, 80]} /><Tooltip contentStyle={{ background: '#111a16', border: '1px solid #395345', borderRadius: 6, color: '#edf4ee', boxShadow: '0 8px 24px #02080680', fontSize: 14 }} labelStyle={{ color: '#b6c7ba', fontSize: 14 }} /><Area type="monotone" dataKey="value" stroke="#397b53" strokeWidth={2} fill="url(#trendFill)" activeDot={{ r: 4, fill: '#397b53', stroke: '#ffffff', strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div><div className="chart-note"><span><i /> Example trend · no verified source connected</span><span>Jan — Dec</span></div></article>
        </section>

        <section className="lower-grid">
                    <article className="panel preparedness-panel"><SectionTitle eyebrow="EXPLAINABLE MODEL" title="Preparedness score" action={<span className="local-tag"><span /> LOCAL DEMO</span>} /><div className="score-overview"><div className="score-ring" style={{ '--score-angle': (score === null ? 0 : score * 3.6) + 'deg' }}><div><strong>{score === null ? '—' : score}</strong><span>/ 100</span></div></div><div className="score-copy"><Badge kind={score === null ? 'signals' : 'watch'}>{score === null ? 'NO LOCAL PROFILE' : 'SYNTHETIC'}</Badge><strong>{score === null ? 'Local demo score unavailable' : 'Local demo estimate'}</strong><p>{score === null ? 'No illustrative profile exists for ' + district.name + '.' : 'Illustrative score for ' + district.name + ', based on editable local demo weights.'}</p><small className="api-score-status">{!selectedApiData ? 'Loading backend score…' : selectedApiData.scoreError ? 'Backend score unavailable: ' + selectedApiData.scoreError : apiScore?.score == null ? 'Backend score ' + (apiScore?.data_status ?? 'unavailable') + ' · no score supplied' : 'Backend score: ' + apiScore.score + ' · ' + apiScore.data_status}</small></div></div><div className="weights-heading"><span>LOCAL DEMO MODEL WEIGHTS</span><span className={totalWeight === 100 ? 'weight-total' : 'weight-total invalid'}>{totalWeight}% total</span></div><div className="weight-list">{weights.map(({ key, label, color }) => <label className="weight-row" key={key}><span className={`weight-dot ${color}`} /><span className="weight-name">{label}</span><input aria-label={`${label} weight`} type="range" min="0" max="80" value={weightsValue[key]} onChange={(event) => updateWeight(key, event.target.value)} className={`range-${color}`} /><span className="weight-value">{weightsValue[key]}%</span></label>)}</div><div className="score-footnote"><CircleHelp size={13} /> Backend score status is shown above. Weight controls update only this local illustrative score.</div></article>

          <article className="panel simulator-panel"><SectionTitle eyebrow="SCENARIO PLANNING" title="Resource readiness" action={<span className="simulator-chip"><Settings2 size={13} /> Simulator</span>} /><p className="sim-intro">Adjust available resources to estimate illustrative coverage for <strong>{district.name}</strong>.</p><div className="resource-list">{[{ key: 'beds', label: 'Staffed beds', unit: 'beds', icon: Stethoscope }, { key: 'rdk', label: 'RDK kits', unit: 'kits', icon: Package }, { key: 'platelets', label: 'Platelet supply', unit: 'units', icon: Droplets }].map(({ key, label, unit, icon: Icon }) => <label className="resource-row" key={key}><span className={`resource-icon ${key}`}><Icon size={16} /></span><span className="resource-label">{label}<small>Available for allocation</small></span><div className="resource-input"><input aria-label={label} type="number" min="0" value={resources[key]} onChange={(event) => updateResource(key, event.target.value)} /><span>{unit}</span></div></label>)}</div><div className="readiness-result"><div><span className="result-kicker">ESTIMATED DEMO READINESS</span><strong>{readiness.label}</strong></div><div className="result-score">{readiness.score}<small>%</small></div></div><div className="readiness-track"><i style={{ width: `${readiness.score}%` }} /></div><div className="readiness-caption"><span>Based on resource inputs only</span><span>Local estimate</span></div><div className="sim-note"><Wind size={13} /> Scenario tool does not represent clinical guidance or actual inventory.</div></article>
        </section>
        </> : activeNav === 'District signals' ? <DistrictSignalsPage district={district} apiData={selectedApiData} /> : activeNav === 'Health indicators' ? <HealthIndicatorsPage district={district} apiData={selectedApiData} score={score} trend={healthTrend} /> : <ResourcePlanningPage district={district} resources={resources} readiness={readiness} updateResource={updateResource} />}
        <footer className="page-footer"><span>AROGYARADAR AI <i>·</i> NEXATHON DEMO</span><span><span className="footer-status" /> {backendHealth === 'connected' ? 'Backend connected' : backendHealth === 'loading' ? 'Connecting to backend' : 'Backend unavailable · local demo fallback'} <i>·</i> Synthetic values remain labeled</span></footer>
      </div>
    </main>
  </div>
}

export default App
