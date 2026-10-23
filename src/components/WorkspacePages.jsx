
import {
  Activity,
  AlertCircle,
  Database,
  Droplets,
  Package,
  Stethoscope,
} from 'lucide-react'

function PanelTitle({ eyebrow, title, action }) {
  return (
    <div className="section-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      {action}
    </div>
  )
}

function Status({ children, kind = '' }) {
  return <span className={`badge ${kind}`}>{children}</span>
}

function InfoPanel({ title, status, children }) {
  return (
    <article
      className="panel workspace-panel"
      aria-busy={status === 'loading'}
    >
      <div className="workspace-panel-heading">
        <h3>{title}</h3>
        <Status
          kind={
            status === 'unavailable' || status === 'error'
              ? 'signals'
              : status === 'demo_only'
                ? 'partial'
                : 'full'
          }
        >
          {status}
        </Status>
      </div>

      {status === 'loading' ? (
        <div
          className="workspace-skeleton"
          role="status"
          aria-label={`Loading ${title}`}
        >
          <i />
          <i />
          <i />
        </div>
      ) : (
        children
      )}
    </article>
  )
}

export function DistrictSignalsPage({ district, apiData }) {
  const history = apiData?.history
  const records = history?.records ?? []
  const score = apiData?.score
  const weather = apiData?.weather

  return (
    <div className="workspace-page">
      <div className="workspace-page-heading">
        <div>
          <span className="eyebrow">DISTRICT INTELLIGENCE</span>
          <h2>{district.name}</h2>
          <p>
            Backend signals available for this district, with source status
            shown for each.
          </p>
        </div>

        <Status kind={district.source === 'api' ? 'full' : 'partial'}>
          {district.source === 'api' ? 'BACKEND DISTRICT' : 'LOCAL FALLBACK'}
        </Status>
      </div>

      <div className="workspace-card-grid">
        <InfoPanel
          title="Weather"
          status={
            !apiData
              ? 'loading'
              : apiData.weatherError
                ? 'error'
                : weather?.data_status ?? 'unavailable'
          }
        >
          {apiData?.weatherError ? (
            <p className="workspace-error">
              <AlertCircle size={15} />
              {apiData.weatherError}
            </p>
          ) : !apiData ? (
            <p>Loading weather response…</p>
          ) : (
            <>
              <p>
                {weather?.source ?? 'Backend weather service'}
                {weather?.data_as_of
                  ? ` · observed ${weather.data_as_of}`
                  : ''}
              </p>

              {weather?.current ? (
                <div className="workspace-metrics">
                  <span>
                    Temperature{' '}
                    <strong>
                      {Number.isFinite(weather.current.temperature_2m)
                        ? `${weather.current.temperature_2m} °C`
                        : 'Not reported'}
                    </strong>
                  </span>

                  <span>
                    Precipitation{' '}
                    <strong>
                      {Number.isFinite(weather.current.precipitation)
                        ? `${weather.current.precipitation} mm`
                        : 'Not reported'}
                    </strong>
                  </span>

                  <span>
                    Humidity{' '}
                    <strong>
                      {Number.isFinite(weather.current.relative_humidity_2m)
                        ? `${weather.current.relative_humidity_2m}%`
                        : 'Not reported'}
                    </strong>
                  </span>
                </div>
              ) : (
                <p>
                  {weather?.message ??
                    'No current weather reading is available.'}
                </p>
              )}
            </>
          )}
        </InfoPanel>

        <InfoPanel
          title="Preparedness score"
          status={
            !apiData
              ? 'loading'
              : apiData.scoreError
                ? 'error'
                : score?.data_status ?? 'unavailable'
          }
        >
          {apiData?.scoreError ? (
            <p className="workspace-error">
              <AlertCircle size={15} />
              {apiData.scoreError}
            </p>
          ) : !apiData ? (
            <p>Loading score status…</p>
          ) : (
            <>
              <p className="workspace-score">
                {score?.score == null ? 'No score available' : score.score}
              </p>

              <p>
                {score?.message ??
                  'The backend has not supplied a district score.'}
              </p>

              {Array.isArray(score?.missing_components) &&
                score.missing_components.length > 0 && (
                  <p>
                    Missing inputs: {score.missing_components.join(', ')}
                  </p>
                )}
            </>
          )}
        </InfoPanel>

        <InfoPanel
          title="Historical health records"
          status={
            !apiData
              ? 'loading'
              : apiData.historyError
                ? 'error'
                : history?.data_status ?? 'unavailable'
          }
        >
          {apiData?.historyError ? (
            <p className="workspace-error">
              <AlertCircle size={15} />
              {apiData.historyError}
            </p>
          ) : !apiData ? (
            <p>Loading historical records…</p>
          ) : records.length > 0 ? (
            <>
              <p className="records-description">
                {history.data_status === 'demo_only'
                  ? 'These are synthetic demonstration records, not verified health statistics.'
                  : 'Historical records supplied by the backend. Check the source and status before interpreting the values.'}
              </p>

              <div className="workspace-records-table-wrap">
                <table className="workspace-records-table">
                  <thead>
                    <tr>
                      <th scope="col">Reporting month</th>
                      <th scope="col">Reported value</th>
                      <th scope="col">Data source</th>
                    </tr>
                  </thead>

                  <tbody>
                    {records.map((record, index) => (
                      <tr key={`${record.month ?? 'record'}-${index}`}>
                        <td>{record.month ?? 'Date not reported'}</td>
                        <td>{record.cases ?? 'Not reported'}</td>
                        <td>
                          <span className="record-source">
                            {record.source ?? 'Source not reported'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="records-footnote">
                {records.length} records returned by the backend. Values and
                units have not been independently verified.
              </p>
            </>
          ) : (
            <p>
              {history?.message ??
                'No historical records are available for this district.'}
            </p>
          )}
        </InfoPanel>
      </div>

      <p className="workspace-disclosure">
        <Database size={14} />
        Backend status is shown as received. Missing values are not estimated.
      </p>
    </div>
  )
}

export function HealthIndicatorsPage({ district, apiData, score, trend }) {
  const weather = apiData?.weather
  const history = apiData?.history
  const backendScore = apiData?.score

  const historyStatus = !apiData
    ? 'loading'
    : apiData.historyError
      ? 'error'
      : history?.data_status ?? 'unavailable'

  const weatherStatus = !apiData
    ? 'loading'
    : apiData.weatherError
      ? 'error'
      : weather?.data_status ?? 'unavailable'

  const scoreStatus = !apiData
    ? 'loading'
    : apiData.scoreError
      ? 'error'
      : backendScore?.data_status ?? 'unavailable'

  const rows = [
    {
      indicator: 'Current weather',
      value: !apiData
        ? 'Loading…'
        : weather?.current
          ? Number.isFinite(weather.current.temperature_2m)
            ? `${weather.current.temperature_2m} °C`
            : 'Temperature not reported'
          : 'No current reading',
      source: weather?.source ?? 'Backend weather endpoint',
      coverage:
        weatherStatus === 'live' || weatherStatus === 'cached'
          ? 'Current reading'
          : !apiData
            ? 'Loading…'
            : 'No reading',
      status: weatherStatus,
    },
    {
      indicator: 'Historical health records',
      value: !apiData
        ? 'Loading…'
        : history?.records?.length
          ? `${history.records.length} records`
          : 'No records',
      source:
        history?.records?.[0]?.source ?? 'Backend history endpoint',
      coverage: history?.records?.length
        ? `${history.records.length} available`
        : !apiData
          ? 'Loading…'
          : 'No coverage',
      status: historyStatus,
    },
    {
      indicator: 'District preparedness score',
      value: !apiData
        ? 'Loading…'
        : backendScore?.score == null
          ? 'Not calculated'
          : backendScore.score,
      source: 'Backend district score endpoint',
      coverage:
        backendScore?.coverage_percent == null
          ? !apiData
            ? 'Loading…'
            : 'Not reported'
          : `${backendScore.coverage_percent}%`,
      status: scoreStatus,
    },
    {
      indicator: 'Composite monthly trend',
      value: `${trend.length} illustrative points`,
      source: 'Local synthetic demo data',
      coverage: 'Illustrative only',
      status: 'demo_only',
    },
    {
      indicator: 'Local district profile',
      value: district.demoInputs
        ? `Illustrative score ${score ?? 'unavailable'}/100`
        : 'No demo profile',
      source: 'Local synthetic demo profile',
      coverage: district.coverage ?? 'No demo coverage',
      status: district.demoInputs ? 'demo_only' : 'unavailable',
    },
  ]

  return (
    <div className="workspace-page">
      <div className="workspace-page-heading">
        <div>
          <span className="eyebrow">DATA CATALOG</span>
          <h2>Health indicators</h2>
          <p>Sources, coverage, and availability for {district.name}.</p>
        </div>

        <Status kind="partial">PROVENANCE VISIBLE</Status>
      </div>

      <article className="panel workspace-panel indicator-panel">
        <div className="indicator-table-wrap">
          <table className="indicator-table">
            <thead>
              <tr>
                <th>Indicator</th>
                <th>Value / availability</th>
                <th>Source</th>
                <th>Coverage</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {rows.map((row) => (
                <tr key={row.indicator}>
                  <th scope="row">{row.indicator}</th>
                  <td>{row.value}</td>
                  <td>{row.source}</td>
                  <td>{row.coverage}</td>
                  <td>
                    <Status
                      kind={
                        row.status === 'live' || row.status === 'cached'
                          ? 'full'
                          : row.status === 'demo_only'
                            ? 'partial'
                            : 'signals'
                      }
                    >
                      {row.status}
                    </Status>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <div className="workspace-card-grid indicator-notes">
        <InfoPanel title="Weather provenance" status={weatherStatus}>
          <p>
            {weather?.source ?? 'Open-Meteo via backend'}.{' '}
            {weather?.data_as_of
              ? `Observed ${weather.data_as_of}.`
              : 'Timestamp is not available.'}{' '}
            Values appear only when supplied by the backend.
          </p>
        </InfoPanel>

        <InfoPanel title="Synthetic data disclosure" status="demo_only">
          <p>
            Trend points and local profile scores are illustrative demo
            values. Backend history may also be labeled demo_only; that
            label is preserved and shown explicitly.
          </p>
        </InfoPanel>
      </div>
    </div>
  )
}

const resourceItems = [
  {
    key: 'beds',
    label: 'Staffed beds',
    unit: 'beds',
    icon: Stethoscope,
  },
  {
    key: 'rdk',
    label: 'RDK kits',
    unit: 'kits',
    icon: Package,
  },
  {
    key: 'platelets',
    label: 'Platelet supply',
    unit: 'units',
    icon: Droplets,
  },
]

export function ResourcePlanningPage({
  district,
  resources,
  readiness,
  updateResource,
}) {
  return (
    <div className="workspace-page">
      <div className="workspace-page-heading">
        <div>
          <span className="eyebrow">SCENARIO PLANNING</span>
          <h2>Resource readiness</h2>
          <p>
            Adjust illustrative resource inputs for {district.name}; estimates
            update immediately.
          </p>
        </div>

        <Status kind="partial">LOCAL DEMO</Status>
      </div>

      <article className="panel planning-panel">
        <PanelTitle
          eyebrow="RESOURCE INPUTS"
          title="Available for allocation"
          action={
            <span className="simulator-chip">
              <Activity size={14} />
              Editable scenario
            </span>
          }
        />

        <div
          className="planning-table-scroll"
          role="region"
          aria-label="Resource planning scenario inputs"
          tabIndex={0}
        >
          <table className="planning-table">
            <thead>
              <tr>
                <th scope="col">Resource</th>
                <th scope="col">Available / planned quantity</th>
                <th scope="col">Required quantity</th>
                <th scope="col">Readiness</th>
                <th scope="col">Status</th>
              </tr>
            </thead>

            <tbody>
              {resourceItems.map(({ key, label, unit, icon: Icon }) => (
                <tr key={key}>
                  <th scope="row">
                    <span className="planning-resource-name">
                      <span className={`resource-icon ${key}`} aria-hidden="true">
                        <Icon size={18} />
                      </span>
                      {label}
                    </span>
                  </th>
                  <td className="planning-quantity-cell">
                    <span className="resource-input">
                      <input
                        aria-label={`${label} available or planned quantity`}
                        type="number"
                        min="0"
                        step="1"
                        value={resources[key]}
                        onChange={(event) =>
                          updateResource(key, event.target.value)
                        }
                      />
                      <span>{unit}</span>
                    </span>
                  </td>
                  <td className="planning-unavailable">Not supplied</td>
                  <td className="planning-aggregate-only">Overall estimate</td>
                  <td><Status kind="partial">DEMO INPUT</Status></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="planning-table-note">
          Required quantities and item-level readiness are not supplied by the
          current model. The estimate below combines the three editable inputs.
        </p>

        <div className="planning-result">
          <div>
            <span className="result-kicker">
              ILLUSTRATIVE READINESS ESTIMATE
            </span>
            <strong>{readiness.label}</strong>
            <p>Calculated locally from the three editable inputs.</p>
          </div>

          <div className="planning-result-score">
            {readiness.score}
            <span>%</span>
          </div>
        </div>

        <div className="planning-track">
          <i style={{ width: `${readiness.score}%` }} />
        </div>

        <p className="planning-disclaimer">
          <AlertCircle size={16} />
          This unvalidated scenario formula is not a medical recommendation,
          verified inventory report, or operational allocation plan.
        </p>
      </article>

      <div className="workspace-card-grid planning-notes">
        <InfoPanel title="Calculation scope" status="demo_only">
          <p>
            The estimate reflects only the current local inputs and existing
            illustrative formula. It does not include district population,
            demand, staffing constraints, or backend inventory.
          </p>
        </InfoPanel>

        <InfoPanel title="Data source" status="demo_only">
          <p>
            Initial values come from the project's synthetic demo defaults.
            Editing fields changes only this browser session's scenario.
          </p>
        </InfoPanel>
      </div>
    </div>
  )
}
