import React, { Component, Suspense, useMemo, useRef } from 'react';
import { Canvas, useLoader, useFrame } from '@react-three/fiber';
import { Bounds, OrbitControls, Center } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import type { FrameApiResponse } from '../src/api';
import type { BufferGeometry, Group } from 'three';
import fallbackStlUrl from '../ressources/steve_block.stl?url';

export interface FrameViewerProps {
    ready: boolean;
    frameData?: FrameApiResponse | null;
    stlUrl?: string;
}

interface ViewerErrorBoundaryProps {
    children: React.ReactNode;
    fallback: React.ReactNode;
}

interface ViewerErrorBoundaryState {
    error?: Error;
}

class ViewerErrorBoundary extends Component<ViewerErrorBoundaryProps, ViewerErrorBoundaryState> {
    state: ViewerErrorBoundaryState = {};

    static getDerivedStateFromError(error: Error): ViewerErrorBoundaryState {
        return { error };
    }

    componentDidCatch(error: Error) {
        console.error('3D frame viewer failed:', error);
    }

    render() {
        if (this.state.error) {
            return (
                <div className="frame-viewer-error" role="alert">
                    {this.props.fallback}
                    <p>{this.state.error.message || 'The generated frame could not be displayed.'}</p>
                </div>
            );
        }
        return this.props.children;
    }
}

// Sub-component to render and animate any passed BufferGeometry directly
function AnimatedSTLModel({ geometry }: { geometry: BufferGeometry }) {
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

// Sub-component to load a remote STL fallback URL via network fetch
function RemoteSTLModel({ url }: { url: string }) {
    const geometry = useLoader(STLLoader, url);
    return <AnimatedSTLModel geometry={geometry} />;
}

export function FrameViewer({
                                ready,
                                frameData,
                                stlUrl = fallbackStlUrl,
                            }: FrameViewerProps) {
    // Synchronously parse base64 STL into BufferGeometry without blob URLs or fetch()
    const parsedGeometry = useMemo(() => {
        if (!frameData?.stl_b64) return null;

        try {
            const binaryString = atob(frameData.stl_b64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const loader = new STLLoader();
            return loader.parse(bytes.buffer);
        } catch (error) {
            console.error('Failed to parse base64 STL string directly:', error);
            return null;
        }
    }, [frameData?.stl_b64]);

    const downloadStl = () => {
        let downloadUrl = stlUrl;
        let createdBlobUrl = false;

        if (frameData?.stl_b64) {
            try {
                const binaryString = atob(frameData.stl_b64);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                const blob = new Blob([bytes.buffer], { type: 'model/stl' });
                downloadUrl = URL.createObjectURL(blob);
                createdBlobUrl = true;
            } catch (error) {
                console.error('Failed to create Blob for STL download:', error);
            }
        }

        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = 'custom-frame.stl';
        link.click();

        if (createdBlobUrl) {
            URL.revokeObjectURL(downloadUrl);
        }
    };

    const downloadSvg = () => {
        // 1. Use the full SVG string returned from the API response
        let svgContent = frameData?.contour_svg;

        // 2. Fallback SVG if frameData or contour_svg is missing
        if (!svgContent) {
            svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="140mm" height="60mm" viewBox="0 0 140 60"><title>Contour OptiFrame</title><g fill="none" stroke="black" stroke-width="1"><ellipse cx="38" cy="30" rx="25" ry="18"/><ellipse cx="102" cy="30" rx="25" ry="18"/><path d="M63 30h14"/></g></svg>`;
        }

        // 3. Create blob and download file
        const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'optiframe-contour.svg';
        link.click();

        // 4. Revoke temporary object URL
        URL.revokeObjectURL(url);
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
                    <ViewerErrorBoundary
                        fallback={
                            <div className="frame-viewer-error" role="alert">
                                <h3>Unable to load the 3D preview</h3>
                                <p>The generated frame could not be displayed.</p>
                                <p>You can still download the generated files below.</p>
                            </div>
                        }
                    >
                        <Canvas camera={{ position: [0, 0, 150], fov: 45 }}>
                            <ambientLight intensity={0.7} />
                            <directionalLight position={[100, 100, 100]} intensity={1.2} />
                            <Suspense fallback={null}>
                                <Bounds fit clip observe margin={1.25}>
                                    <Center>
                                        {parsedGeometry ? (
                                            <AnimatedSTLModel
                                                key={frameData?.stl_b64}
                                                geometry={parsedGeometry}
                                            />
                                        ) : (
                                            <RemoteSTLModel key={stlUrl} url={stlUrl} />
                                        )}
                                    </Center>
                                </Bounds>
                            </Suspense>
                            <OrbitControls enableZoom makeDefault />
                        </Canvas>
                    </ViewerErrorBoundary>
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