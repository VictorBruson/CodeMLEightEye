import { useState } from 'react';
import { Camera } from '../components/Camera';
import { FrameCustomizer, type FrameOptions } from '../components/FrameCustomizer';
import { FrameViewer } from '../components/FrameViewer';
import { MeasurementOverlay } from '../components/MeasurementOverlay';
import './App.css';

interface LensPhoto {
  url: string;
  measurements: Record<string, number>;
}

type Screen = 'home' | 'left' | 'right' | 'results' | 'design';

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [left, setLeft] = useState<LensPhoto>();
  const [right, setRight] = useState<LensPhoto>();
  const [options, setOptions] = useState<FrameOptions>({ bridge: 18, rim: 0.2, eye: 'left' });
  const [showReference, setShowReference] = useState(false);

  const addPhoto = (side: 'left' | 'right', url: string) => {
    const measurements = side === 'left'
      ? { width: 51, height: 37, perimeter: 139 }
      : { width: 50, height: 36, perimeter: 137 };
    (side === 'left' ? setLeft : setRight)({ url, measurements });
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
        <a className="mobile-brand" href="/" aria-label="OptiFrame home">
          <span className="brand-mark">◒</span> Opti<span>Frame</span>
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
          <div className="screen-copy">
            <span className="eyebrow">Step 1 of 3</span>
            <h1>Capture the<br /><em>left lens.</em></h1>
            <p>Place the lens and card in the frame, then take a clear photo from above.</p>
          </div>
          <Camera eye="left" imageUrl={left?.url} autoStart={!showReference} onCapture={(_, url) => addPhoto('left', url)} />
          {left && <button className="button button--primary next-button" type="button" onClick={() => setScreen('right')}>Next: right lens <span>→</span></button>}
        </section>
      )}

      {screen === 'right' && (
        <section className="mobile-screen capture-screen">
          <div className="screen-copy">
            <span className="eyebrow">Step 2 of 3</span>
            <h1>Now capture the<br /><em>right lens.</em></h1>
            <p>Keep the same setup and make sure the entire lens is visible.</p>
          </div>
          <Camera eye="right" imageUrl={right?.url} onCapture={(_, url) => addPhoto('right', url)} />
          {right && <button className="button button--primary next-button" type="button" onClick={() => setScreen('results')}>See measurements <span>→</span></button>}
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
            <div className="result-card"><h3>Left lens</h3><MeasurementOverlay imageUrl={left?.url} measurements={left?.measurements} /></div>
            <div className="result-card"><h3>Right lens</h3><MeasurementOverlay imageUrl={right?.url} measurements={right?.measurements} /></div>
          </div>
          <button className="button button--primary next-button" type="button" onClick={() => setScreen('design')}>Design my frame <span>→</span></button>
        </section>
      )}

      {screen === 'design' && (
        <section className="mobile-screen design-screen">
          <FrameViewer options={options} ready={Boolean(left && right)} />
          <FrameCustomizer options={options} onChange={setOptions} />
        </section>
      )}
      {showReference && (
        <div className="modal-backdrop" role="presentation">
          <section className="reference-modal" role="dialog" aria-modal="true" aria-labelledby="reference-title">
            <button className="modal-close" type="button" onClick={() => setShowReference(false)} aria-label="Close instructions">×</button>
            <div className="instruction-art instruction-art--modal" aria-hidden="true">
              <div className="credit-card"><span>VISA</span><i /></div>
              <div className="instruction-lens" />
            </div>
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
