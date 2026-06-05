import React from 'react';
import './App.css';
import { Status } from '../status';
import { RGB, StatusInfo } from '../../models';
import { StatusButton } from '../statusButton';
import { content } from '../../content';

type MatrixMode = 'available' | 'busy' | 'away' | 'outOfOffice' | 'appearOffline' | 'doNotDisturb' | 'rainbow' | 'on' | 'off' | 'unknown';

const statusDetails = {
  available: {
    label: content.statuses.available.label,
    description: content.statuses.available.description,
    rgb: { red: 0, green: 144, blue: 0 },
    matrix: 'available' as MatrixMode,
  },
  busy: {
    label: content.statuses.busy.label,
    description: content.statuses.busy.description,
    rgb: { red: 179, green: 0, blue: 0 },
    matrix: 'busy' as MatrixMode,
  },
  away: {
    label: content.statuses.away.label,
    description: content.statuses.away.description,
    rgb: { red: 255, green: 191, blue: 0 },
    matrix: 'away' as MatrixMode,
  },
  outofoffice: {
    label: content.statuses.outOfOffice.label,
    description: content.statuses.outOfOffice.description,
    rgb: { red: 0, green: 86, blue: 179 },
    matrix: 'outOfOffice' as MatrixMode,
  },
  appearoffline: {
    label: content.statuses.appearOffline.label,
    description: content.statuses.appearOffline.description,
    rgb: { red: 128, green: 128, blue: 128 },
    matrix: 'appearOffline' as MatrixMode,
  },
  donotdisturb: {
    label: content.statuses.doNotDisturb.label,
    description: content.statuses.doNotDisturb.description,
    rgb: { red: 128, green: 0, blue: 128 },
    matrix: 'doNotDisturb' as MatrixMode,
  },
  rainbow: {
    label: content.statuses.rainbow.label,
    description: content.statuses.rainbow.description,
    rgb: null,
    matrix: 'rainbow' as MatrixMode,
  },
  on: {
    label: content.statuses.on.label,
    description: content.statuses.on.description,
    rgb: null,
    matrix: 'on' as MatrixMode,
  },
  off: {
    label: content.statuses.off.label,
    description: content.statuses.off.description,
    rgb: { red: 112, green: 120, blue: 130 },
    matrix: 'off' as MatrixMode,
  },
};

type StatusKey = keyof typeof statusDetails;

const normalizeStatus = (value: string | null): StatusKey | null => {
  if (!value) {
    return null;
  }

  const key = value.toLowerCase() as StatusKey;
  return statusDetails[key] ? key : null;
};

const matrixWidth = 17;
const matrixHeight = 7;

const matrixColor = (mode: MatrixMode, x: number, y: number): string | null => {
  if (mode === 'available') {
    return 'rgb(0, 144, 0)';
  }

  if (mode === 'busy') {
    return 'rgb(179, 0, 0)';
  }

  if (mode === 'away') {
    return 'rgb(255, 191, 0)';
  }

  if (mode === 'outOfOffice') {
    return 'rgb(0, 86, 179)';
  }

  if (mode === 'appearOffline') {
    return 'rgb(128, 128, 128)';
  }

  if (mode === 'doNotDisturb') {
    return 'rgb(128, 0, 128)';
  }

  if (mode === 'rainbow') {
    const hue = Math.round(((x / (matrixWidth - 1)) * 300) + (y * 8));
    return `hsl(${hue}, 90%, 52%)`;
  }

  if (mode === 'on') {
    const colors = ['rgb(35, 113, 255)', 'rgb(0, 180, 120)', 'rgb(255, 191, 0)', 'rgb(179, 0, 0)'];
    return colors[(x + (y * 2)) % colors.length];
  }

  return null;
};

const MatrixPreview: React.FunctionComponent<{ mode: MatrixMode; small?: boolean }> = ({ mode, small }) => {
  const cells = [];
  for (let y = 0; y < matrixHeight; y++) {
    for (let x = 0; x < matrixWidth; x++) {
      const color = matrixColor(mode, x, y);
      cells.push(
        <span
          className={`matrix-dot${color ? ' lit' : ''}`}
          key={`${x}-${y}`}
          style={color ? { backgroundColor: color, color } : undefined}
        />
      );
    }
  }

  return (
    <div className={`matrix-preview${small ? ' small' : ''}`} aria-hidden="true">
      {cells}
    </div>
  );
};

const Navigation: React.FunctionComponent<{ view: 'home' | 'docs'; setView: (view: 'home' | 'docs') => void }> = ({ view, setView }) => (
  <nav className="app-nav" aria-label="Navegacion principal">
    <a
      className={view === 'home' ? 'active' : ''}
      href="#"
      onClick={() => setView('home')}>
      {content.navigation.home}
    </a>
    <a
      className={view === 'docs' ? 'active' : ''}
      href="#api-docs"
      onClick={() => setView('docs')}>
      {content.navigation.apiDocs}
    </a>
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
        <span role="columnheader">{content.docs.descriptionLabel}</span>
      </div>
      {content.docs.endpoints.map((endpoint) => (
        <div className="docs-row" role="row" key={endpoint.endpoint}>
          <span className="method-list" role="cell">
            {endpoint.methods.map((method) => (
              <code key={method}>{method}</code>
            ))}
          </span>
          <code className="endpoint" role="cell">{endpoint.endpoint}</code>
          <span role="cell">{endpoint.description}</span>
        </div>
      ))}
    </div>
  </section>
);

export function App() {
  const timer = React.useRef<number | null>(null);
  const mounted = React.useRef<boolean>(false);
  const [status, setStatus] = React.useState<string | null>(null);
	const [rgb, setRgb] = React.useState<RGB | null>(null);
	const [overwritten, setStatusOverwritten] = React.useState<boolean>(false);
  const [view, setView] = React.useState<'home' | 'docs'>(() => window.location.hash === '#api-docs' ? 'docs' : 'home');

  const fetchStatus = React.useCallback(async () => {
    try {
      const data = await fetch(`/api/status`);

      if (data && data.ok) {
        const statusInfo: StatusInfo = await data.json();
        if (statusInfo && statusInfo.status) {
          setStatus(statusInfo.status);
          setRgb({
            red: statusInfo.red,
            green: statusInfo.green,
            blue: statusInfo.blue,
          });
          setStatusOverwritten(!!statusInfo.statusOverwritten);
        } else {
          setStatus(null);
          setRgb(null);
          setStatusOverwritten(false);
        }
      }

    } finally {
      if (!mounted.current) {
        return;
      }
      if (timer.current) {
        clearTimeout(timer.current);
      }
      timer.current = window.setTimeout(() => {
        fetchStatus();
      }, (1 * 60 * 1000));
    }
  }, []);

	React.useEffect(() => {
    mounted.current = true;
    fetchStatus();
    return () => {
      mounted.current = false;
      if (timer.current) {
        clearTimeout(timer.current);
      }
    };
  }, [fetchStatus]);

  React.useEffect(() => {
    const handleHashChange = () => {
      setView(window.location.hash === '#api-docs' ? 'docs' : 'home');
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const callApi = async (url: string) => {
    if (url) {
      const data = await fetch(url, { method: "POST", body: JSON.stringify({}) });
      if (data && data.ok) {
        if (timer.current) {
          clearTimeout(timer.current);
        }
        fetchStatus();
      }
    }
  };

  const statusKey = normalizeStatus(status);
  const currentStatus = statusKey ? statusDetails[statusKey] : {
    label: content.emptyState.label,
    description: content.emptyState.description,
    rgb: null,
    matrix: 'unknown' as MatrixMode,
  };
  const displayRgb = rgb || currentStatus.rgb;

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
      <Status
        status={status}
        rgb={displayRgb}
        label={currentStatus.label}
        description={currentStatus.description}
        preview={<MatrixPreview mode={currentStatus.matrix} />}
      />

      <section className="status-grid" aria-label={content.sections.statuses}>
        <StatusButton apiUrl={"/api/available"} className={"available"} text={content.statuses.available.label} description={content.statuses.available.buttonDescription} preview={<MatrixPreview mode="available" small />} active={statusKey === 'available'} callApi={callApi} />
        <StatusButton apiUrl={"/api/busy"} className={"busy"} text={content.statuses.busy.label} description={content.statuses.busy.buttonDescription} preview={<MatrixPreview mode="busy" small />} active={statusKey === 'busy'} callApi={callApi} />
        <StatusButton apiUrl={"/api/away"} className={"away"} text={content.statuses.away.label} description={content.statuses.away.buttonDescription} preview={<MatrixPreview mode="away" small />} active={statusKey === 'away'} callApi={callApi} />
        <StatusButton apiUrl={"/api/out-of-office"} className={"out-of-office"} text={content.statuses.outOfOffice.label} description={content.statuses.outOfOffice.buttonDescription} preview={<MatrixPreview mode="outOfOffice" small />} active={statusKey === 'outofoffice'} callApi={callApi} />
        <StatusButton apiUrl={"/api/appear-offline"} className={"appear-offline"} text={content.statuses.appearOffline.label} description={content.statuses.appearOffline.buttonDescription} preview={<MatrixPreview mode="appearOffline" small />} active={statusKey === 'appearoffline'} callApi={callApi} />
        <StatusButton apiUrl={"/api/do-not-disturb"} className={"do-not-disturb"} text={content.statuses.doNotDisturb.label} description={content.statuses.doNotDisturb.buttonDescription} preview={<MatrixPreview mode="doNotDisturb" small />} active={statusKey === 'donotdisturb'} callApi={callApi} />
        <StatusButton apiUrl={"/api/rainbow"} className={"rainbow"} text={content.statuses.rainbow.label} description={content.statuses.rainbow.buttonDescription} preview={<MatrixPreview mode="rainbow" small />} active={statusKey === 'rainbow'} callApi={callApi} />
      </section>

      <section className="power-grid" aria-label={content.sections.power}>
        <StatusButton apiUrl={"/api/on"} className={"power-on"} text={content.statuses.on.label} preview={<MatrixPreview mode="on" small />} active={statusKey === 'on'} callApi={callApi} />
        <StatusButton apiUrl={"/api/off"} className={"power-off"} text={content.statuses.off.label} preview={<MatrixPreview mode="off" small />} active={statusKey === 'off'} callApi={callApi} />
      </section>

      {
        overwritten && (
          <section className="reset-row">
            <StatusButton apiUrl={"/api/reset"} className={"reset"} text={content.actions.resetOverride} callApi={callApi} />
          </section>
        )
      }
		</main>
  );
}
