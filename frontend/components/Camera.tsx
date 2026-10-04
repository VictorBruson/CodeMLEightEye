import { useEffect, useRef, useState } from 'react';

export interface CameraProps {
  eye: 'left' | 'right';
  imageUrl?: string;
  autoStart?: boolean;
  onCapture?: (image: Blob, imageUrl: string) => void;
}

export function Camera({ eye, imageUrl, autoStart = false, onCapture }: CameraProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return;

    video.srcObject = stream;
    const playVideo = () => {
      video.play().catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        console.error('Video play error:', err);
      });
    };

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      playVideo();
    } else {
      video.addEventListener('loadedmetadata', playVideo, { once: true });
    }

    return () => {
      video.removeEventListener('loadedmetadata', playVideo);
    };
  }, [cameraOpen]);

  const startCamera = async () => {
    setError(undefined);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Live camera is not available here. You can upload a photo instead.');
      return;
    }
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });
      setCameraOpen(true);
    } catch (err: any) {
      console.error("Camera error:", err);
      setError(`Camera error: ${err.name || err.message || 'Access declined'}`);
    }
  };

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (autoStart && !imageUrl && !cameraOpen) void startCamera();
  }, [autoStart]);

  const captureFrame = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      onCapture?.(blob, url);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraOpen(false);
    }, 'image/jpeg', 0.92);
  };

  const handleFile = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Choose a JPG, PNG, or HEIC image.');
      return;
    }
    setError(undefined);
    onCapture?.(file, URL.createObjectURL(file));
  };

  return (
    <section className="capture-card">
      <div className="capture-card__heading">
        <div>
          <span className="eyebrow">{eye === 'left' ? 'Step 1 of 3' : 'Step 2 of 3'}</span>
          <h2>Capture the {eye === 'left' ? 'left' : 'right'} lens.</h2>
          <p className="capture-instruction">
            {eye === 'left'
              ? 'Place the lens and card in the frame, then take a clear photo from above.'
              : 'Keep the same setup and make sure the entire lens is visible.'}
          </p>
        </div>
        {imageUrl && <span className="status-pill">Photo added</span>}
      </div>
      <div className={`capture-preview ${imageUrl ? 'capture-preview--filled' : ''}`}>
        {imageUrl ? (
          <img src={imageUrl} alt={`Photo of the ${eye === 'left' ? 'left' : 'right'} lens`} />
        ) : cameraOpen ? (
          <div className="live-camera">
            <video ref={videoRef} autoPlay playsInline muted aria-label="Live camera preview" />
            <span className="camera-guide" aria-hidden="true" />
            <button className="capture-shutter" type="button" onClick={captureFrame} aria-label="Take photo" />
          </div>
        ) : (
          <div className="capture-empty">
            <span className="camera-icon" aria-hidden="true">⌾</span>
            <strong>Place the lens flat</strong>
            <span>Include the reference marker in the frame.</span>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => handleFile(event.target.files?.[0])}
      />
      {!imageUrl && !cameraOpen && <button className="button button--primary button--full" type="button" onClick={startCamera}>Open camera</button>}
      {imageUrl && <button className="button button--primary button--full" type="button" onClick={startCamera}>Retake photo</button>}
      {!cameraOpen && <button className="upload-link" type="button" onClick={() => inputRef.current?.click()}>Upload an existing photo instead</button>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}
