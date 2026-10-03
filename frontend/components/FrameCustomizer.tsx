export interface FrameOptions {
  bridge: number;
  rim: number;
  eye: 'left' | 'right';
}

export interface FrameCustomizerProps {
  options: FrameOptions;
  onChange: (options: FrameOptions) => void;
}

export function FrameCustomizer({ options, onChange }: FrameCustomizerProps) {
  const update = (key: keyof FrameOptions, value: number | FrameOptions['eye']) => {
    onChange({ ...options, [key]: value });
  };

  return (
    <section className="panel customizer">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Step 3</span>
          <h2>Customize the frame</h2>
        </div>
        <span className="step-count">3 / 3</span>
      </div>
      <label className="field-label" htmlFor="eye-select">Lens orientation</label>
      <select id="eye-select" value={options.eye} onChange={(event) => update('eye', event.target.value as FrameOptions['eye'])}>
        <option value="left">Nasal side is on the right (left eye)</option>
        <option value="right">Nasal side is on the left (right eye)</option>
      </select>
      <div className="field-row">
        <label className="field-label" htmlFor="bridge">Bridge width <output>{options.bridge} mm</output></label>
        <input id="bridge" type="range" min="12" max="28" value={options.bridge} onChange={(event) => update('bridge', Number(event.target.value))} />
      </div>
      <div className="field-row">
        <label className="field-label" htmlFor="rim">Clip clearance <output>{options.rim.toFixed(1)} mm</output></label>
        <input id="rim" type="range" min="0.1" max="0.5" step="0.1" value={options.rim} onChange={(event) => update('rim', Number(event.target.value))} />
      </div>
    </section>
  );
}
