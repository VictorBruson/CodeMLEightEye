import React, { Suspense, useMemo } from 'react';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls, Center } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import type { FrameOptions } from './FrameCustomizer';

export interface FrameApiResponse {
    version: number;
    stl_b64: string;
    left: { eye: string; A: number; B: number; perimeter: number };
    right: { eye: string; A: number; B: number; perimeter: number };
    dbl_mm: number;
    bbox_mm: [number, number, number];
    validation: { watertight: boolean; single_body: boolean; overhang_fraction: number };
    warnings: string[];
}

export interface FrameViewerProps {
    options: FrameOptions;
    ready: boolean;
    frameData?: FrameApiResponse | null;
    stlUrl?: string;
}

function STLModel({ url }: { url: string }) {
    const geometry = useLoader(STLLoader, url);

    return (
        <mesh geometry={geometry} castShadow receiveShadow>
            <meshStandardMaterial color="#222222" roughness={0.3} metalness={0.2} />
        </mesh>
    );
}

export function FrameViewer({
                                options: _options,
                                ready,
                                frameData,
                                stlUrl = 'ressources/steve_block.stl',
                            }: FrameViewerProps) {
    // Convert base64 STL to a Blob URL if stl_b64 is present
    const activeStlUrl = useMemo(() => {
        if (!frameData?.stl_b64) return stlUrl;

        try {
            // Decode base64 to binary byte array
            const binaryString = atob(frameData.stl_b64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const blob = new Blob([bytes.buffer], { type: 'model/stl' });
            return URL.createObjectURL(blob);
        } catch (error) {
            console.error('Failed to parse base64 STL string:', error);
            return stlUrl;
        }
    }, [frameData?.stl_b64, stlUrl]);

    // Clean up object URL on unmount or URL change
    React.useEffect(() => {
        return () => {
            if (activeStlUrl && activeStlUrl.startsWith('blob:')) {
                URL.revokeObjectURL(activeStlUrl);
            }
        };
    }, [activeStlUrl]);

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
                <span className="preview-badge">3D STL</span>
            </div>

            <div
                className={`frame-preview ${ready ? 'frame-preview--ready' : ''}`}
                style={{ height: '320px', width: '100%', position: 'relative' }}
            >
                {ready ? (
                    <Canvas camera={{ position: [0, 0, 150], fov: 45 }}>
                        <ambientLight intensity={0.7} />
                        <directionalLight position={[100, 100, 100]} intensity={1.2} />
                        <Suspense fallback={null}>
                            <Center>
                                <STLModel url={activeStlUrl} />
                            </Center>
                        </Suspense>
                        <OrbitControls enableZoom makeDefault />
                    </Canvas>
                ) : (
                    <p>Add both photos to generate the preview.</p>
                )}
            </div>

            {frameData && (
                <div className="frame-metrics" style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
                    <p>
                        <strong>Bounding Box:</strong> {frameData.bbox_mm.join(' × ')} mm |{' '}
                        <strong>Bridge (DBL):</strong> {frameData.dbl_mm} mm
                    </p>
                </div>
            )}

            <div className="viewer-footer">
                <p>
                    <span className="status-dot" />{' '}
                    {ready ? 'Model ready to review' : 'Waiting for measurements'}
                </p>
                <button
                    className="button button--secondary"
                    type="button"
                    onClick={downloadSvg}
                    disabled={!ready}
                >
                    Export SVG contour
                </button>
            </div>
        </section>
    );
}