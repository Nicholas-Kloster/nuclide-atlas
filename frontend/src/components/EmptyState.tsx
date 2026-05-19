interface Props {
  onAddSource: () => void;
}

export function EmptyState({ onAddSource }: Props) {
  return (
    <div className="empty-state">
      <h2>No stack to map yet</h2>
      <p>
        Atlas needs something to render. Pick one:
      </p>
      <ul>
        <li>
          <code>bin/atlas-bootstrap</code> from the repo root scans your machine
          for LLM services and writes <code>config/atlas.yaml</code>.
        </li>
        <li>
          <code>bin/atlas-demo</code> spawns mock services on loopback so you can
          see Atlas work with no real stack.
        </li>
        <li>
          Click <strong>+ Add source</strong> below to paste a base URL or
          re-discover from inside the browser.
        </li>
      </ul>
      <button className="primary" onClick={onAddSource}>+ Add source</button>
    </div>
  );
}
