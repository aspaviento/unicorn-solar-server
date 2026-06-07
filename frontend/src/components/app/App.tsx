import React from 'react';
import './App.css';
import { content } from '../../content';

type Flow = 'charging' | 'discharging' | 'exporting';
type BarColor = 'blue' | 'green' | 'red' | 'yellow';
type Tariff = 'low' | 'medium' | 'high';
type SolarStatus = {
  percentage: number;
  activeBars: number;
  flow: Flow;
  barColor: BarColor;
  tariff: Tariff;
};

const barColors: Record<BarColor, string> = {
  blue: 'rgb(30, 120, 255)',
  green: 'rgb(0, 180, 80)',
  red: 'rgb(230, 55, 60)',
  yellow: 'rgb(255, 190, 0)',
};
const tariffColors: Record<Tariff, string> = {
  low: 'rgb(0, 180, 80)',
  medium: 'rgb(255, 190, 0)',
  high: 'rgb(230, 55, 60)',
};
const barStartColumns = [14, 11, 8, 5, 2];
const solaredgeExample = `{
  "siteCurrentPowerFlow": {
    "connections": [
      { "from": "PV", "to": "Load" },
      { "from": "LOAD", "to": "Grid" }
    ],
    "GRID": { "status": "Active", "currentPower": 3.59 },
    "LOAD": { "status": "Active", "currentPower": 0.41 },
    "PV": { "status": "Active", "currentPower": 4.0 },
    "STORAGE": {
      "status": "Idle",
      "currentPower": 0.0,
      "chargeLevel": 99,
      "critical": false
    }
  }
}`;

function pixelColor(status: SolarStatus, x: number, y: number) {
  if (x === 0 && [2, 3, 4].includes(y)) return tariffColors[status.tariff];
  if ((y === 0 || y === 6) && x >= 1) return 'rgb(245, 248, 252)';
  if ((x === 1 || x === 16) && y >= 1 && y <= 5) return 'rgb(245, 248, 252)';
  for (const start of barStartColumns.slice(0, status.activeBars)) {
    if ((x === start || x === start + 1) && y >= 1 && y <= 5) return barColors[status.barColor];
  }
  return null;
}

function BatteryPreview({ status }: { status: SolarStatus }) {
  return (
    <div className="matrix-preview" aria-label={content.panel.batteryAriaLabel(status.percentage)}>
      {Array.from({ length: 119 }, (_, index) => {
        const x = index % 17;
        const y = Math.floor(index / 17);
        const color = pixelColor(status, x, y);
        return <span className={`matrix-dot${color ? ' lit' : ''}`} key={index} style={color ? { backgroundColor: color, color } : undefined} />;
      })}
    </div>
  );
}

const Navigation: React.FunctionComponent<{ view: 'home' | 'docs'; setView: (view: 'home' | 'docs') => void }> = ({ view, setView }) => (
  <nav className="app-nav" aria-label={content.navigation.ariaLabel}>
    <a className={view === 'home' ? 'active' : ''} href="#" onClick={() => setView('home')}>{content.navigation.home}</a>
    <a className={view === 'docs' ? 'active' : ''} href="#api-docs" onClick={() => setView('docs')}>{content.navigation.apiDocs}</a>
  </nav>
);

const ApiDocs: React.FunctionComponent = () => (
  <section className="docs-panel">
    <header className="docs-header">
      <span className="status-kicker">{content.appName}</span>
      <h1>{content.docs.title}</h1>
      <p>{content.docs.description}</p>
    </header>
    <div className="docs-table" role="table" aria-label={content.docs.title}>
      <div className="docs-row docs-row-header" role="row">
        <span role="columnheader">{content.docs.methodLabel}</span>
        <span role="columnheader">{content.docs.endpointLabel}</span>
        <span role="columnheader">{content.docs.requestLabel}</span>
        <span role="columnheader">{content.docs.descriptionLabel}</span>
      </div>
      {content.docs.endpoints.map((endpoint) => (
        <div className="docs-row" role="row" key={endpoint.endpoint}>
          <span className="method-list" role="cell">
            {endpoint.methods.map((method) => <code key={method}>{method}</code>)}
          </span>
          <code className="endpoint" role="cell">{endpoint.endpoint}</code>
          <code className="request-body" role="cell">{endpoint.request}</code>
          <span role="cell">{endpoint.description}</span>
        </div>
      ))}
    </div>
  </section>
);

export function App() {
  const [status, setStatus] = React.useState<SolarStatus>({
    percentage: 0,
    activeBars: 0,
    flow: 'charging',
    barColor: 'green',
    tariff: 'medium',
  });
  const [percentage, setPercentage] = React.useState(0);
  const [solaredgeJson, setSolaredgeJson] = React.useState(solaredgeExample);
  const [solaredgeMessage, setSolaredgeMessage] = React.useState('');
  const [solaredgeError, setSolaredgeError] = React.useState(false);
  const [solaredgeApplying, setSolaredgeApplying] = React.useState(false);
  const [view, setView] = React.useState<'home' | 'docs'>(() => window.location.hash === '#api-docs' ? 'docs' : 'home');

  const applyStatus = React.useCallback((nextStatus: SolarStatus) => {
    setStatus(nextStatus);
    setPercentage(nextStatus.percentage);
  }, []);

  const refresh = React.useCallback(async () => {
    const response = await fetch('/api/status');
    if (response.ok) applyStatus(await response.json());
  }, [applyStatus]);

  React.useEffect(() => { refresh(); }, [refresh]);
  React.useEffect(() => {
    const handleHashChange = () => setView(window.location.hash === '#api-docs' ? 'docs' : 'home');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const post = async (endpoint: string, body: object) => {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (response.ok) applyStatus(await response.json());
  };

  const applySolaredgeJson = async () => {
    let payload: object;
    try {
      payload = JSON.parse(solaredgeJson);
    } catch {
      setSolaredgeError(true);
      setSolaredgeMessage(content.panel.solaredgeInvalidJson);
      return;
    }

    setSolaredgeApplying(true);
    setSolaredgeMessage('');
    try {
      const response = await fetch('/api/solaredge-interface', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        setSolaredgeError(true);
        setSolaredgeMessage(content.panel.apiError(result.error ?? response.statusText));
        return;
      }
      applyStatus(result);
      setSolaredgeError(false);
      setSolaredgeMessage(content.panel.solaredgeSuccess);
    } catch (error) {
      setSolaredgeError(true);
      setSolaredgeMessage(content.panel.apiError(error instanceof Error ? error.message : String(error)));
    } finally {
      setSolaredgeApplying(false);
    }
  };

  if (view === 'docs') {
    return (
      <main className="app-shell">
        <Navigation view={view} setView={setView} />
        <ApiDocs />
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Navigation view={view} setView={setView} />
      <section className="status-panel">
        <div className="status-led"><BatteryPreview status={status} /></div>
        <div className="status-copy">
          <span className="status-kicker">{content.appName}</span>
          <h1>{status.percentage}%</h1>
          <p>{content.panel.statusSummary(content.panel.flows[status.flow], content.panel.tariffs[status.tariff], status.activeBars)}</p>
        </div>
      </section>

      <section className="control-panel">
        <h2>{content.panel.batterySection}</h2>
        <label htmlFor="percentage">{content.panel.percentageLabel(percentage)}</label>
        <input id="percentage" type="range" min="0" max="100" value={percentage} onChange={(event) => setPercentage(Number(event.target.value))} />
        <div className="button-row">
          {(['charging', 'discharging', 'exporting'] as Flow[]).map((flow) => (
            <button
              key={flow}
              disabled={flow === 'exporting' && percentage !== 100}
              onClick={() => post('/api/battery', { percentage, flow })}>
              {content.panel.flows[flow]}
            </button>
          ))}
        </div>
      </section>

      <section className="control-panel">
        <h2>{content.panel.tariffSection}</h2>
        <div className="button-row">
          {(['low', 'medium', 'high'] as Tariff[]).map((level) => (
            <button key={level} onClick={() => post('/api/tariff', { level })}>{content.panel.tariffs[level]}</button>
          ))}
        </div>
      </section>

      <section className="control-panel">
        <h2>{content.panel.solaredgeSection}</h2>
        <p className="control-description">{content.panel.solaredgeDescription}</p>
        <label htmlFor="solaredge-json">{content.panel.solaredgeLabel}</label>
        <textarea
          id="solaredge-json"
          className="json-input"
          spellCheck={false}
          value={solaredgeJson}
          placeholder={content.panel.solaredgePlaceholder}
          onChange={(event) => setSolaredgeJson(event.target.value)}
        />
        <div className="button-row">
          <button disabled={solaredgeApplying} onClick={applySolaredgeJson}>
            {solaredgeApplying ? content.panel.solaredgeApplying : content.panel.solaredgeSubmit}
          </button>
        </div>
        {solaredgeMessage && (
          <p className={`form-message${solaredgeError ? ' error' : ' success'}`} role="status">
            {solaredgeMessage}
          </p>
        )}
      </section>

      <section className="control-panel">
        <h2>{content.panel.displaySection}</h2>
        <div className="button-row">
          <button onClick={() => post('/api/rainbow', {})}>{content.panel.rainbow}</button>
          <button onClick={() => post('/api/off', {})}>{content.panel.off}</button>
        </div>
      </section>
    </main>
  );
}
