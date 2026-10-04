import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useLoader, useFrame } from '@react-three/fiber';
import { OrbitControls, Center } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import type { Group } from 'three';

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
    ready: boolean;
    frameData?: FrameApiResponse | null;
    stlUrl?: string;
}

// Sub-component to handle the slower drop & spin animation
function AnimatedSTLModel({ url }: { url: string }) {
    const geometry = useLoader(STLLoader, url);
    const groupRef = useRef<Group>(null);
    const animProgress = useRef(0);

    useFrame((_, delta) => {
        if (animProgress.current < 1) {
            // Slower animation speed (takes ~3 seconds to complete)
            animProgress.current = Math.min(animProgress.current + delta * 0.35, 1);
            const p = animProgress.current;

            // Smooth ease-out cubic curve
            const easeOut = 1 - Math.pow(1 - p, 3);

            if (groupRef.current) {
                // Gentle drop from y = 60 down to 0
                groupRef.current.position.y = (1 - easeOut) * 60;
                // Graceful 360-degree spin during drop
                groupRef.current.rotation.y = (1 - easeOut) * Math.PI * 2;
            }
        }
    });

    return (
        <group ref={groupRef}>
            <mesh geometry={geometry} castShadow receiveShadow>
                <meshStandardMaterial color="#222222" roughness={0.3} metalness={0.2} />
            </mesh>
        </group>
    );
}

export function FrameViewer({
                                ready,
                                frameData,
                                stlUrl = 'ressources/steve_block.stl',
                            }: FrameViewerProps) {
    // Convert base64 STL to a Blob URL if stl_b64 is present
    const activeStlUrl = useMemo(() => {
        if (!frameData?.stl_b64) return stlUrl;

        try {
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

    const downloadStl = () => {
        const link = document.createElement('a');
        link.href = activeStlUrl;
        link.download = 'custom-frame.stl';
        link.click();
    };

    const downloadSvg = () => {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="140mm" height="60mm" viewBox="0 0 140 60"><title>Contour OptiFrame</title><g fill="none" stroke="black" stroke-width="1"><ellipse cx="38" cy="30" rx="25" ry="18"/><ellipse cx="102" cy="30" rx="25" ry="18"/><path d="M63 30h14"/></g></svg>`;
        const link = document.createElement('a');
        link.href = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
        link.download = 'optiframe-contour.svg';
        link.click();
        URL.revokeObjectURL(link.href);
    };

    return (
        <section className="panel viewer" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="section-heading">
                <div>
                    <span className="eyebrow">3D Preview</span>
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
                                <AnimatedSTLModel key={activeStlUrl} url={activeStlUrl} />
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

            <div className="viewer-status" style={{ margin: '1rem 0 0.5rem 0' }}>
                <p style={{ margin: 0 }}>
                    <span className="status-dot" />{' '}
                    {ready ? 'Model ready to download' : 'Waiting for measurements'}
                </p>
            </div>

            {/* Action buttons at the bottom */}
            <div className="viewer-actions" style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingTop: '1rem' }}>
                <button
                    className="button button--primary button--full"
                    type="button"
                    onClick={downloadStl}
                    disabled={!ready}
                    style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}
                >
                    Download STL <span>↓</span>
                </button>
                <button
                    className="button button--secondary"
                    type="button"
                    onClick={downloadSvg}
                    disabled={!ready}
                    style={{ width: '100%' }}
                >
                    Export SVG contour
                </button>
            </div>
        </section>
    );
}