import type { FrameOptions } from './FrameCustomizer';

export interface FrameViewerProps {
  options: FrameOptions;
  ready: boolean;
}

export function FrameViewer({ options, ready }: FrameViewerProps) {
  const downloadSvg = () => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="140mm" height="60mm" viewBox="0 0 140 60"><title>Contour OptiFrame</title><g fill="none" stroke="black" stroke-width="1"><ellipse cx="38" cy="30" rx="25" ry="18"/><ellipse cx="102" cy="30" rx="25" ry="18"/><path d="M63 30h14"/></g></svg>`;
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    link.download = 'optiframe-contour.svg';
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <section className="panel viewer">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Preview</span>
          <h2>Your frame</h2>
        </div>
        <span className="preview-badge">3D</span>
      </div>
      <div className={`frame-preview ${ready ? 'frame-preview--ready' : ''}`}>
        <div className="glasses" style={{ gap: `${options.bridge * 1.8}px` }}>
          <span className="lens lens--left" />
          <span className="bridge" />
          <span className="lens lens--right" />
        </div>
        {!ready && <p>Add both photos to generate the preview.</p>}
      </div>
      <div className="viewer-footer">
        <p><span className="status-dot" /> {ready ? 'Model ready to review' : 'Waiting for measurements'}</p>
        <button className="button button--secondary" type="button" onClick={downloadSvg} disabled={!ready}>Export SVG contour</button>
      </div>
    </section>
  );
}
