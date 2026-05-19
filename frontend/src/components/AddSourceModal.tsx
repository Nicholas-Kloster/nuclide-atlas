import { useState } from 'react';
import { postDiscover, postImportUrl } from '../lib/api';

interface Props {
  onClose: () => void;
  onChanged: () => void;
}

type Tab = 'discover' | 'url';

export function AddSourceModal({ onClose, onChanged }: Props) {
  const [tab, setTab] = useState<Tab>('discover');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState('');
  const [hostInput, setHostInput] = useState('');
  const [includeDocker, setIncludeDocker] = useState(true);
  const [includeEnv, setIncludeEnv] = useState(true);
  const [includeLocal, setIncludeLocal] = useState(true);

  const runDiscover = async () => {
    setBusy(true);
    setErr(null);
    setInfo(null);
    try {
      const extra = hostInput
        .split(',')
        .map((h) => h.trim())
        .filter(Boolean);
      const r = await postDiscover({
        include_env: includeEnv,
        include_local: includeLocal,
        include_docker: includeDocker,
        extra_hosts: extra,
      });
      setInfo(`${r.graph_summary} · sources: ${r.sources_run.join(', ')}`);
      onChanged();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const runImport = async () => {
    if (!urlInput.trim()) return;
    setBusy(true);
    setErr(null);
    setInfo(null);
    try {
      const r = await postImportUrl(urlInput.trim());
      setInfo(r.graph_summary);
      onChanged();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <header>
          <h2>+ Add source</h2>
          <button onClick={onClose} aria-label="close">×</button>
        </header>
        <nav className="tabs">
          <button
            className={tab === 'discover' ? 'active' : ''}
            onClick={() => setTab('discover')}
          >
            Auto-discover
          </button>
          <button
            className={tab === 'url' ? 'active' : ''}
            onClick={() => setTab('url')}
          >
            Probe a URL
          </button>
        </nav>

        {tab === 'discover' && (
          <div className="modal-body">
            <p>
              Scans env vars, localhost ports, and Docker for known LLM services
              and rewrites the graph.
            </p>
            <label>
              <input
                type="checkbox"
                checked={includeEnv}
                onChange={(e) => setIncludeEnv(e.target.checked)}
              />{' '}
              Env vars (OPENAI_API_BASE, OLLAMA_HOST, …)
            </label>
            <label>
              <input
                type="checkbox"
                checked={includeLocal}
                onChange={(e) => setIncludeLocal(e.target.checked)}
              />{' '}
              localhost port catalog
            </label>
            <label>
              <input
                type="checkbox"
                checked={includeDocker}
                onChange={(e) => setIncludeDocker(e.target.checked)}
              />{' '}
              docker ps
            </label>
            <label className="stack">
              Additional hosts (comma-separated)
              <input
                type="text"
                value={hostInput}
                placeholder="10.0.0.5, gpu-node-2.lan"
                onChange={(e) => setHostInput(e.target.value)}
              />
            </label>
            <div className="actions">
              <button className="primary" disabled={busy} onClick={runDiscover}>
                {busy ? 'Discovering…' : 'Run discovery'}
              </button>
            </div>
          </div>
        )}

        {tab === 'url' && (
          <div className="modal-body">
            <p>
              Atlas probes the URL against the standard health paths
              (<code>/v1/models</code>, <code>/api/tags</code>,{' '}
              <code>/info</code>, …) and merges the result.
            </p>
            <label className="stack">
              Base URL
              <input
                type="text"
                value={urlInput}
                placeholder="http://my-llm.internal:8000"
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runImport()}
                autoFocus
              />
            </label>
            <div className="actions">
              <button
                className="primary"
                disabled={busy || !urlInput.trim()}
                onClick={runImport}
              >
                {busy ? 'Probing…' : 'Probe and merge'}
              </button>
            </div>
          </div>
        )}

        {(info || err) && (
          <footer className={err ? 'err' : 'info'}>
            {err ?? info}
          </footer>
        )}
      </div>
    </div>
  );
}
