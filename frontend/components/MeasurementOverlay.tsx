export interface MeasurementOverlayProps {
  imageUrl?: string;
  measurements?: {
    width?: number;
    height?: number;
  };
}

export function MeasurementOverlay({ imageUrl, measurements }: MeasurementOverlayProps) {
  if (!imageUrl) {
    return (
      <div className="measurement-empty">
        <span className="measurement-empty__icon" aria-hidden="true">⌁</span>
        <p>Measurements will appear after you add a photo.</p>
      </div>
    );
  }

  return (
    <div className="measurement-result">
      <div className="measurement-image">
        <img src={imageUrl} alt="Measured contour preview" />
      </div>
      <div className="measurement-stats">
        <div><span>Width A</span><strong>{measurements?.width ?? '—'}{measurements?.width !== undefined && ' mm'}</strong></div>
        <div><span>Height B</span><strong>{measurements?.height ?? '—'}{measurements?.height !== undefined && ' mm'}</strong></div>
      </div>
    </div>
  );
}
