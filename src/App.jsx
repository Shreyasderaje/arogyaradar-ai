import { useMemo, useState } from 'react'
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Bell, ChevronDown, CircleHelp, CloudRain, Database, Droplets, HeartPulse, Layers3, MapPin, Menu, Package, Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Stethoscope, Wind, X } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { districts, healthTrend, initialWeights, resourceDefaults } from './data/demoData'
import { calculateDemoScore, estimateReadiness } from './services/dashboardService'
import DistrictMap from './components/DistrictMap'
import './App.css'
import './Redesign.css'
import './Typography.css'

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
function SectionTitle({ eyebrow, title, action }) { return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action}</div> }

function App() {
  const [districtId, setDistrictId] = useState(districts[0].id)
  const [activeNav, setActiveNav] = useState('Overview')
  const [weightsValue, setWeightsValue] = useState(initialWeights)
  const [resources, setResources] = useState(resourceDefaults)
  const [mobileOpen, setMobileOpen] = useState(false)
  const district = districts.find((item) => item.id === districtId)
  const score = useMemo(() => calculateDemoScore(district, weightsValue), [district, weightsValue])
  const readiness = useMemo(() => estimateReadiness(resources), [resources])
  const totalWeight = Object.values(weightsValue).reduce((sum, weight) => sum + Number(weight), 0)

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
      <div className="workspace-label">WORKSPACE</div>
      <nav className="nav-list" aria-label="Main navigation">{navItems.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activeNav === label ? 'active' : ''}`} onClick={() => { setActiveNav(label); setMobileOpen(false) }}><Icon size={17} /><span>{label}</span>{label === 'District signals' && <span className="nav-count">08</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="coverage-note"><div className="note-icon"><ShieldCheck size={16} /></div><div><strong>Demo workspace</strong><p>All figures are synthetic</p></div></div><button className="nav-item"><Settings2 size={17} /><span>Settings</span></button><button className="nav-item"><CircleHelp size={17} /><span>Help & documentation</span></button><div className="profile"><div className="avatar">AR</div><div className="profile-copy"><strong>Analyst workspace</strong><small>Demo access</small></div><ChevronDown size={15} className="muted-icon" /></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="header-left"><button className="mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumbs"><span>Workspace</span><span className="crumb-sep">/</span><strong>{activeNav}</strong></div></div><div className="header-actions"><span className="freshness"><span className="live-dot" /> Demo dataset <span className="fresh-sep">Â·</span> Updated today, 09:40</span><button className="icon-button notification" aria-label="Notifications"><Bell size={17} /><i /></button><div className="user-chip"><span className="avatar small-avatar">AR</span><ChevronDown size={14} /></div></div></header>
      <div className="content">
        <section className="page-intro"><div><div className="intro-kicker"><span className="kicker-line" /> NEXATHON Â· HEALTH INTELLIGENCE</div><h1>Good morning, analyst<span className="title-period">.</span></h1><p>Signals for a clearer picture of community health.</p></div><label className="district-select-wrap"><span>SELECTED DISTRICT</span><div className="select-control"><MapPin size={16} /><select aria-label="Selected district" value={districtId} onChange={(event) => setDistrictId(event.target.value)}>{districts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><ChevronDown size={15} className="select-chevron" /></div></label></section>
        <div className="demo-banner"><span className="demo-banner-icon"><Sparkles size={15} /></span><div><strong>SYNTHETIC DEMO DATA</strong><span> Illustrative values only Â· Not verified health statistics</span></div><button aria-label="About demo data" title="All values on this dashboard are synthetic and for demonstration only"><CircleHelp size={15} /></button></div>

        <section className="summary-grid" aria-label="Dashboard summary">
          <article className="summary-card"><div className="summary-top"><span className="summary-icon coral"><AlertTriangle size={17} /></span><span className="summary-label">DISTRICTS TO REVIEW</span><span className="trend down"><ArrowDownRight size={14} /> 2</span></div><div className="summary-value">08<span className="summary-unit"> / 31</span></div><div className="summary-foot"><span>Demo signal threshold</span><span className="inline-link">View districts <ArrowUpRight size={12} /></span></div><div className="mini-bars" aria-hidden="true">{[24, 37, 31, 51, 42, 63, 47, 74, 55, 82, 65, 72, 52, 67, 45, 59, 39, 49, 29, 44, 33, 54, 37, 48].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div></article>
          <article className="summary-card"><div className="summary-top"><span className="summary-icon blue-icon"><CloudRain size={17} /></span><span className="summary-label">WEATHER SIGNALS</span><span className="soft-tag">7 day window</span></div><div className="summary-value">12<span className="summary-unit"> active</span></div><div className="summary-foot"><span>Across demo districts</span><span className="signal-status"><span className="signal-dot" /> Monitoring</span></div><div className="weather-visual"><div className="weather-line"><span>Rainfall anomaly</span><b>Elevated</b></div><div className="progress-track"><i style={{ width: '68%' }} /></div><div className="weather-line"><span>Heat index</span><b className="neutral-text">Moderate</b></div><div className="progress-track muted-track"><i style={{ width: '42%' }} /></div></div></article>
          <article className="summary-card"><div className="summary-top"><span className="summary-icon mint-icon"><Database size={17} /></span><span className="summary-label">DATA COVERAGE</span><span className="soft-tag">Current view</span></div><div className="summary-value">76<span className="summary-unit">%</span></div><div className="summary-foot"><span>Across selected indicators</span><Badge kind="partial">PARTIAL</Badge></div><div className="coverage-meter"><i style={{ width: '76%' }} /></div><div className="coverage-breakdown"><span><i className="full-key" /> 18 full</span><span><i className="partial-key" /> 9 partial</span><span><i className="signals-key" /> 4 signals only</span></div></article>
        </section>

        <section className="primary-grid">
          <article className="panel map-panel"><SectionTitle eyebrow="GEOGRAPHIC OVERVIEW" title="District signal map" action={<button className="quiet-action"><SlidersHorizontal size={14} /> Layers</button>} /><DistrictMap districts={districts} selectedDistrictId={districtId} weights={weightsValue} onSelectDistrict={setDistrictId} /><div className="map-foot"><div className="selected-place"><span className="place-pin"><MapPin size={14} /></span><span><strong>{district.name}</strong><small>Selected district Â· Synthetic profile</small></span></div><Badge kind={district.coverage.toLowerCase().replace(' ', '-')}>{district.coverage}</Badge></div></article>
          <article className="panel trend-panel"><SectionTitle eyebrow="HISTORICAL SIGNAL" title="Monthly indicator trend" action={<button className="period-select">Last 12 months <ChevronDown size={13} /></button>} /><div className="chart-subtitle"><span className="chart-legend" /> Composite demo indicator <span className="chart-units">INDEX Â· ILLUSTRATIVE</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={healthTrend} margin={{ top: 12, right: 5, left: -5, bottom: 0 }}><defs><linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4fba9b" stopOpacity={0.2} /><stop offset="100%" stopColor="#4fba9b" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#252d38" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#798391', fontSize: 12 }} dy={10} /><YAxis domain={[20, 80]} axisLine={false} tickLine={false} tick={{ fill: '#798391', fontSize: 12 }} ticks={[20, 40, 60, 80]} /><Tooltip contentStyle={{ background: '#171e28', border: '1px solid #303b49', borderRadius: 9, color: '#e8edf4', fontSize: 14 }} labelStyle={{ color: '#98a4b2', fontSize: 14 }} /><Area type="monotone" dataKey="value" stroke="#54c6a4" strokeWidth={2} fill="url(#trendFill)" activeDot={{ r: 4, fill: '#54c6a4', stroke: '#121923', strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div><div className="chart-note"><span><i /> Example trend Â· no verified source connected</span><span>Jan â€” Dec</span></div></article>
        </section>

        <section className="lower-grid">
          <article className="panel preparedness-panel"><SectionTitle eyebrow="EXPLAINABLE MODEL" title="Preparedness score" action={<span className="local-tag"><span /> LOCAL DEMO</span>} /><div className="score-overview"><div className="score-ring" style={{ '--score-angle': `${score * 3.6}deg` }}><div><strong>{score}</strong><span>/ 100</span></div></div><div className="score-copy"><Badge kind="watch">WATCH</Badge><strong>Moderate preparedness</strong><p>Illustrative score for {district.name}, based on editable demo weights.</p></div></div><div className="weights-heading"><span>MODEL WEIGHTS</span><span className={totalWeight === 100 ? 'weight-total' : 'weight-total invalid'}>{totalWeight}% total</span></div><div className="weight-list">{weights.map(({ key, label, color }) => <label className="weight-row" key={key}><span className={`weight-dot ${color}`} /><span className="weight-name">{label}</span><input aria-label={`${label} weight`} type="range" min="0" max="80" value={weightsValue[key]} onChange={(event) => updateWeight(key, event.target.value)} className={`range-${color}`} /><span className="weight-value">{weightsValue[key]}%</span></label>)}</div><div className="score-footnote"><CircleHelp size={13} /> Adjust a weight to redistribute the remaining share. Local demo calculation only.</div></article>

          <article className="panel simulator-panel"><SectionTitle eyebrow="SCENARIO PLANNING" title="Resource readiness" action={<span className="simulator-chip"><Settings2 size={13} /> Simulator</span>} /><p className="sim-intro">Adjust available resources to estimate illustrative coverage for <strong>{district.name}</strong>.</p><div className="resource-list">{[{ key: 'beds', label: 'Staffed beds', unit: 'beds', icon: Stethoscope }, { key: 'rdk', label: 'RDK kits', unit: 'kits', icon: Package }, { key: 'platelets', label: 'Platelet supply', unit: 'units', icon: Droplets }].map(({ key, label, unit, icon: Icon }) => <label className="resource-row" key={key}><span className={`resource-icon ${key}`}><Icon size={16} /></span><span className="resource-label">{label}<small>Available for allocation</small></span><div className="resource-input"><input aria-label={label} type="number" min="0" value={resources[key]} onChange={(event) => updateResource(key, event.target.value)} /><span>{unit}</span></div></label>)}</div><div className="readiness-result"><div><span className="result-kicker">ESTIMATED DEMO READINESS</span><strong>{readiness.label}</strong></div><div className="result-score">{readiness.score}<small>%</small></div></div><div className="readiness-track"><i style={{ width: `${readiness.score}%` }} /></div><div className="readiness-caption"><span>Based on resource inputs only</span><span>Local estimate</span></div><div className="sim-note"><Wind size={13} /> Scenario tool does not represent clinical guidance or actual inventory.</div></article>
        </section>
        <footer className="page-footer"><span>AROGYARADAR AI <i>Â·</i> NEXATHON DEMO</span><span><span className="footer-status" /> No backend connected <i>Â·</i> All data is synthetic</span></footer>
      </div>
    </main>
  </div>
}

export default App
