import { Activity, AlertCircle, Database, Droplets, Package, Stethoscope } from 'lucide-react'

function PanelTitle({ eyebrow, title, action }) {
  return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action}</div>
}

function Status({ children, kind = '' }) {
  return <span className={`badge ${kind}`}>{children}</span>
}

function InfoPanel({ title, status, children }) {
  return <article className="panel workspace-panel" aria-busy={status === 'loading'}><div className="workspace-panel-heading"><h3>{title}</h3><Status kind={status === 'unavailable' || status === 'error' ? 'signals' : status === 'demo_only' ? 'partial' : 'full'}>{status}</Status></div>{status === 'loading' ? <div className="workspace-skeleton" role="status" aria-label={`Loading ${title}`}><i /><i /><i /></div> : children}</article>
}

export function DistrictSignalsPage({ district, apiData }) {
  const history = apiData?.history
  const records = history?.records ?? []
  const score = apiData?.score
  const weather = apiData?.weather

  return <div className="workspace-page">
    <div className="workspace-page-heading"><div><span className="eyebrow">DISTRICT INTELLIGENCE</span><h2>{district.name}</h2><p>Backend signals available for this district, with source status shown for each.</p></div><Status kind={district.source === 'api' ? 'full' : 'partial'}>{district.source === 'api' ? 'BACKEND DISTRICT' : 'LOCAL FALLBACK'}</Status></div>
    <div className="workspace-card-grid">
      <InfoPanel title="Weather" status={apiData ? (apiData.weatherError ? 'error' : weather?.data_status ?? 'unavailable') : 'loading'}>
        {apiData?.weatherError ? <p className="workspace-error"><AlertCircle size={15} />{apiData.weatherError}</p> : apiData ? <><p>{weather?.source ?? 'Backend weather service'}{weather?.data_as_of ? ` · observed ${weather.data_as_of}` : ''}</p>{weather?.current ? <div className="workspace-metrics"><span>Temperature <strong>{Number.isFinite(weather.current.temperature_2m) ? `${weather.current.temperature_2m} °C` : 'Not reported'}</strong></span><span>Precipitation <strong>{Number.isFinite(weather.current.precipitation) ? `${weather.current.precipitation} mm` : 'Not reported'}</strong></span><span>Humidity <strong>{Number.isFinite(weather.current.relative_humidity_2m) ? `${weather.current.relative_humidity_2m}%` : 'Not reported'}</strong></span></div> : <p>{weather?.message ?? 'No current weather reading is available.'}</p>}</> : <p>Loading weather response…</p>}
      </InfoPanel>
      <InfoPanel title="Preparedness score" status={!apiData ? 'loading' : apiData.scoreError ? 'error' : score?.data_status ?? 'unavailable'}>
        {apiData?.scoreError ? <p className="workspace-error"><AlertCircle size={15} />{apiData.scoreError}</p> : !apiData ? <p>Loading score status…</p> : <><p className="workspace-score">{score?.score == null ? 'No score available' : score.score}</p><p>{score?.message ?? 'The backend has not supplied a district score.'}</p>{Array.isArray(score?.missing_components) && score.missing_components.length > 0 && <p>Missing inputs: {score.missing_components.join(', ')}</p>}</>}
      </InfoPanel>
      <InfoPanel title="Historical health records" status={!apiData ? 'loading' : apiData.historyError ? 'error' : history?.data_status ?? 'unavailable'}>
        {apiData?.historyError ? <p className="workspace-error"><AlertCircle size={15} />{apiData.historyError}</p> : !apiData ? <p>Loading history response…</p> : records.length ? <><p>{history.data_status === 'demo_only' ? 'Synthetic backend demo records; not verified health statistics.' : 'Records returned by the backend. Review source and status before interpretation.'}</p><div className="workspace-records"><div><span>Month</span><span>Value</span><span>Source</span></div>{records.map((record, index) => <div key={`${record.month ?? 'record'}-${index}`}><span>{record.month ?? 'Date not reported'}</span><span>{record.cases ?? 'Not reported'}</span><span>{record.source ?? 'Not reported'}</span></div>)}</div></> : <p>{history?.message ?? 'No historical records are available for this district.'}</p>}
      </InfoPanel>
    </div>
    <p className="workspace-disclosure"><Database size={14} /> Backend status is shown as received. Missing values are not estimated.</p>
  </div>
}

export function HealthIndicatorsPage({ district, apiData, score, trend }) {
  const weather = apiData?.weather
  const history = apiData?.history
  const backendScore = apiData?.score
  const historyStatus = !apiData ? 'loading' : apiData.historyError ? 'error' : history?.data_status ?? 'unavailable'
  const weatherStatus = !apiData ? 'loading' : apiData.weatherError ? 'error' : weather?.data_status ?? 'unavailable'
  const scoreStatus = !apiData ? 'loading' : apiData.scoreError ? 'error' : backendScore?.data_status ?? 'unavailable'
  const rows = [
    { indicator: 'Current weather', value: !apiData ? 'Loading…' : weather?.current ? `${Number.isFinite(weather.current.temperature_2m) ? weather.current.temperature_2m + ' °C' : 'Temperature not reported'}` : 'No current reading', source: weather?.source ?? 'Backend weather endpoint', coverage: weatherStatus === 'live' || weatherStatus === 'cached' ? 'Current reading' : !apiData ? 'Loading…' : 'No reading', status: weatherStatus },
    { indicator: 'Historical health records', value: !apiData ? 'Loading…' : history?.records?.length ? `${history.records.length} records` : 'No records', source: history?.records?.[0]?.source ?? 'Backend history endpoint', coverage: history?.records?.length ? `${history.records.length} available` : !apiData ? 'Loading…' : 'No coverage', status: historyStatus },
    { indicator: 'District preparedness score', value: !apiData ? 'Loading…' : backendScore?.score == null ? 'Not calculated' : backendScore.score, source: 'Backend district score endpoint', coverage: backendScore?.coverage_percent == null ? (!apiData ? 'Loading…' : 'Not reported') : `${backendScore.coverage_percent}%`, status: scoreStatus },
    { indicator: 'Composite monthly trend', value: `${trend.length} illustrative points`, source: 'Local synthetic demo data', coverage: 'Illustrative only', status: 'demo_only' },
    { indicator: 'Local district profile', value: district.demoInputs ? `Illustrative score ${score ?? 'unavailable'}/100` : 'No demo profile', source: 'Local synthetic demo profile', coverage: district.coverage ?? 'No demo coverage', status: district.demoInputs ? 'demo_only' : 'unavailable' },
  ]

  return <div className="workspace-page">
    <div className="workspace-page-heading"><div><span className="eyebrow">DATA CATALOG</span><h2>Health indicators</h2><p>Sources, coverage, and availability for {district.name}.</p></div><Status kind="partial">PROVENANCE VISIBLE</Status></div>
    <article className="panel workspace-panel indicator-panel"><div className="indicator-table-wrap"><table className="indicator-table"><thead><tr><th>Indicator</th><th>Value / availability</th><th>Source</th><th>Coverage</th><th>Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.indicator}><th scope="row">{row.indicator}</th><td>{row.value}</td><td>{row.source}</td><td>{row.coverage}</td><td><Status kind={row.status === 'live' || row.status === 'cached' ? 'full' : row.status === 'demo_only' ? 'partial' : 'signals'}>{row.status}</Status></td></tr>)}</tbody></table></div></article>
    <div className="workspace-card-grid indicator-notes">
      <InfoPanel title="Weather provenance" status={weatherStatus}><p>{weather?.source ?? 'Open-Meteo via backend'}. {weather?.data_as_of ? `Observed ${weather.data_as_of}.` : 'Timestamp is not available.'} Values appear only when supplied by the backend.</p></InfoPanel>
      <InfoPanel title="Synthetic data disclosure" status="demo_only"><p>Trend points and local profile scores are illustrative demo values. Backend history may also be labeled demo_only; that label is preserved and shown explicitly.</p></InfoPanel>
    </div>
  </div>
}

const resourceItems = [
  { key: 'beds', label: 'Staffed beds', unit: 'beds', icon: Stethoscope },
  { key: 'rdk', label: 'RDK kits', unit: 'kits', icon: Package },
  { key: 'platelets', label: 'Platelet supply', unit: 'units', icon: Droplets },
]

export function ResourcePlanningPage({ district, resources, readiness, updateResource }) {
  return <div className="workspace-page">
    <div className="workspace-page-heading"><div><span className="eyebrow">SCENARIO PLANNING</span><h2>Resource readiness</h2><p>Adjust illustrative resource inputs for {district.name}; estimates update immediately.</p></div><Status kind="partial">LOCAL DEMO</Status></div>
    <article className="panel planning-panel"><PanelTitle eyebrow="RESOURCE INPUTS" title="Available for allocation" action={<span className="simulator-chip"><Activity size={14} /> Editable scenario</span>} /><div className="planning-resource-list">{resourceItems.map(({ key, label, unit, icon: Icon }) => <label className="planning-resource-row" key={key}><span className={`resource-icon ${key}`}><Icon size={18} /></span><span className="resource-label">{label}<small>Illustrative input only; not verified inventory</small></span><span className="resource-input"><input aria-label={`${label} scenario input`} type="number" min="0" step="1" value={resources[key]} onChange={(event) => updateResource(key, event.target.value)} /><span>{unit}</span></span></label>)}</div>
      <div className="planning-result"><div><span className="result-kicker">ILLUSTRATIVE READINESS ESTIMATE</span><strong>{readiness.label}</strong><p>Calculated locally from the three editable inputs.</p></div><div className="planning-result-score">{readiness.score}<span>%</span></div></div><div className="planning-track"><i style={{ width: `${readiness.score}%` }} /></div><p className="planning-disclaimer"><AlertCircle size={16} /> This unvalidated scenario formula is not a medical recommendation, verified inventory report, or operational allocation plan.</p>
    </article>
    <div className="workspace-card-grid planning-notes"><InfoPanel title="Calculation scope" status="demo_only"><p>The estimate reflects only the current local inputs and existing illustrative formula. It does not include district population, demand, staffing constraints, or backend inventory.</p></InfoPanel><InfoPanel title="Data source" status="demo_only"><p>Initial values come from the project's synthetic demo defaults. Editing fields changes only this browser session's scenario.</p></InfoPanel></div>
  </div>
}
