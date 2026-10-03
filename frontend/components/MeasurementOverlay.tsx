export interface MeasurementOverlayProps {
  imageUrl?: string;
  measurements?: Record<string, number>;
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
        <div className="measurement-outline" aria-hidden="true">
          <span className="measure-line measure-line--width" />
          <span className="measure-line measure-line--height" />
        </div>
        <span className="measure-label measure-label--width">{measurements?.width ?? 50} mm</span>
        <span className="measure-label measure-label--height">{measurements?.height ?? 36} mm</span>
      </div>
      <div className="measurement-stats">
        <div><span>Width A</span><strong>{measurements?.width ?? 50} mm</strong></div>
        <div><span>Height B</span><strong>{measurements?.height ?? 36} mm</strong></div>
        <div><span>Perimeter</span><strong>{measurements?.perimeter ?? 137} mm</strong></div>
      </div>
    </div>
  );
}
