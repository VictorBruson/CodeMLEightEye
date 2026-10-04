import { useState } from 'react';
import { Camera } from '../components/Camera';
import { FrameViewer } from '../components/FrameViewer';
import { MeasurementOverlay } from '../components/MeasurementOverlay';
import { generateFrame, measurePair, type FrameApiResponse } from './api';
import './App.css';

interface LensPhoto {
  blob: Blob;
  url: string;
  measurements: Record<string, number>;
  overlay?: string;
  contract?: Record<string, unknown>;
}

type Screen = 'home' | 'left' | 'right' | 'results' | 'design';

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [left, setLeft] = useState<LensPhoto>();
  const [right, setRight] = useState<LensPhoto>();
  const [showReference, setShowReference] = useState(false);
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [measurementError, setMeasurementError] = useState<string>();
  const [setFrameData] = useState<FrameApiResponse>();
  const [frameError, setFrameError] = useState<string>();
  const [isGeneratingFrame, setIsGeneratingFrame] = useState(false);

  const addPhoto = (side: 'left' | 'right', blob: Blob, url: string) => {
    (side === 'left' ? setLeft : setRight)({ blob, url, measurements: {} });
    setMeasurementError(undefined);
  };

  const measureCapturedPair = async () => {
    if (!left || !right) return;
    setIsMeasuring(true);
    setMeasurementError(undefined);
    try {
      const result = await measurePair(left.blob, right.blob);
      setLeft({ ...left, contract: result.contract, overlay: result.overlays.left, measurements: {
        width: result.measurements.left.A_mm,
        height: result.measurements.left.B_mm,
      }});
      setRight({ ...right, contract: result.contract, overlay: result.overlays.right, measurements: {
        width: result.measurements.right.A_mm,
        height: result.measurements.right.B_mm,
      }});
      setScreen('results');
    } catch (error) {
      setMeasurementError(error instanceof Error ? error.message : 'The lens images could not be measured.');
    } finally {
      setIsMeasuring(false);
    }
  };

  const generateMeasuredFrame = async () => {
    if (!left?.contract) return;
    setIsGeneratingFrame(true);
    setFrameError(undefined);
    try {
      setFrameData(await generateFrame(left.contract));
      setScreen('design');
    } catch (error) {
      setFrameError(error instanceof Error ? error.message : 'The frame could not be generated.');
    } finally {
      setIsGeneratingFrame(false);
    }
  };

  const currentStep = screen === 'left' ? 1 : screen === 'right' ? 2 : screen === 'results' ? 3 : 0;
  const goBack = () => {
    const previous: Partial<Record<Screen, Screen>> = {
      left: 'home',
      right: 'left',
      results: 'right',
      design: 'results',
    };
    setScreen(previous[screen] ?? 'home');
  };

  return (
      <main className={`mobile-app mobile-app--${screen}`}>
        <header className="mobile-header">
          {screen !== 'home' ? (
              <button className="icon-button" type="button" onClick={goBack} aria-label="Go back">←</button>
          ) : <span className="header-spacer" />}
          <a className="mobile-brand" href="/" aria-label="EightEye home">
            <span className="brand-mark">8</span> Eight<span>Eye</span>
          </a>
          {currentStep > 0 ? <span className="step-indicator">{currentStep} / 3</span> : <span className="header-spacer" />}
        </header>

        {screen === 'home' && (
            <section className="mobile-screen home-screen">
              <div className="home-art" aria-hidden="true">
                <span className="home-lens home-lens--one" />
                <span className="home-lens home-lens--two" />
                <span className="home-spark">✦</span>
              </div>
              <div className="screen-copy">
                <span className="eyebrow">Custom eyewear, made simple</span>
                <h1>Give your lenses<br /><em>a new frame.</em></h1>
                <p>Measure your recycled lenses and create a custom 3D-printable frame in a few steps.</p>
              </div>
              <button className="button button--primary start-button" type="button" onClick={() => { setScreen('left'); setShowReference(true); }}>Get started <span>→</span></button>
              <p className="privacy-note">No account needed · Photos stay on your device</p>
            </section>
        )}

        {screen === 'left' && (
            <section className="mobile-screen capture-screen">
              <Camera eye="left" imageUrl={left?.url} autoStart={!showReference} onCapture={(blob, url) => addPhoto('left', blob, url)} />
              {left && <button className="button button--primary next-button" type="button" onClick={() => setScreen('right')}>Next: right lens <span>→</span></button>}
            </section>
        )}

        {screen === 'right' && (
            <section className="mobile-screen capture-screen">
              <Camera eye="right" imageUrl={right?.url} onCapture={(blob, url) => addPhoto('right', blob, url)} />
              {measurementError && <p className="form-error" role="alert">{measurementError}</p>}
              {right && <button className="button button--primary next-button" type="button" onClick={() => void measureCapturedPair()} disabled={isMeasuring}>{isMeasuring ? 'Measuring both lenses…' : 'See measurements'} <span>→</span></button>}
            </section>
        )}

      {screen === 'results' && (
        <section className="mobile-screen results-screen">
          <div className="screen-copy">
            <span className="eyebrow">Step 3 of 3</span>
            <h1>Your lens<br /><em>measurements.</em></h1>
            <p>These measurements will guide your custom frame.</p>
          </div>
          <div className="mobile-results">
            <div className="result-card"><h3>Left lens</h3><MeasurementOverlay imageUrl={left?.overlay ?? left?.url} measurements={left?.measurements} /></div>
            <div className="result-card"><h3>Right lens</h3><MeasurementOverlay imageUrl={right?.overlay ?? right?.url} measurements={right?.measurements} /></div>
          </div>
          {frameError && <p className="form-error" role="alert">{frameError}</p>}
          <button className="button button--primary next-button" type="button" onClick={() => void generateMeasuredFrame()} disabled={isGeneratingFrame}>{isGeneratingFrame ? 'Generating frame…' : 'Design my frame'} <span>→</span></button>
        </section>
      )}

        {screen === 'design' && (
            <section className="mobile-screen design-screen">
              <FrameViewer ready={Boolean(left && right)} />
            </section>
        )}
        {screen === 'left' && showReference && (
            <div className="modal-backdrop" role="presentation">
              <section className="reference-modal" role="dialog" aria-modal="true" aria-labelledby="reference-title">
                <button className="modal-close" type="button" onClick={() => setShowReference(false)} aria-label="Close instructions">×</button>
                <img className="reference-photo" src="/lens-card-reference.svg" alt="A lens and credit card aligned side by side" />
                <span className="eyebrow">Before you take the photo</span>
                <h2 id="reference-title">Place your lens next to a card.</h2>
                <p>A standard bank or credit card gives us a known size to measure your lens accurately. Put both on a flat, plain surface.</p>
                <button className="button button--primary button--full" type="button" onClick={() => setShowReference(false)}>Got it, open camera <span>→</span></button>
              </section>
            </div>
        )}
      </main>
  );
}

export default App;
