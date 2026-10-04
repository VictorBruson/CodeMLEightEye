import React, { useState, useEffect, useMemo, useRef } from 'react';

export interface ContractLens {
    eye: 'L' | 'R';
    points_mm: [number, number][];
    flipped?: boolean;
    params?: Record<string, number>;
    [key: string]: unknown;
}

export interface BuildContract {
    left: ContractLens;
    right: ContractLens;
    dbl_mm: number;
    params?: Record<string, number>;
    [key: string]: unknown;
}

interface LensParams {
    clearance: number;
    wall: number;
    groove_depth: number;
    lens_edge_thickness: number;
}

interface LensEditorProps {
    isOpen: boolean;
    onClose: () => void;
    initialContract: BuildContract;
    onUpdateContract: (updatedContract: BuildContract) => Promise<void> | void;
    isGenerating?: boolean;
}

export const LensEditor: React.FC<LensEditorProps> = ({
                                                          isOpen,
                                                          onClose,
                                                          initialContract,
                                                          onUpdateContract,
                                                          isGenerating = false,
                                                      }) => {
    const [selectedEye, setSelectedEye] = useState<'L' | 'R'>('L');
    const [dbl, setDbl] = useState<number>(initialContract.dbl_mm ?? 18);

    // Helper to extract params with fallbacks: Lens params -> Global params -> Defaults
    const extractParams = (lens?: ContractLens): LensParams => ({
        clearance: (lens?.params?.clearance as number) ?? (initialContract.params?.clearance as number) ?? 0.2,
        wall: (lens?.params?.wall as number) ?? (initialContract.params?.wall as number) ?? 3.0,
        groove_depth: (lens?.params?.groove_depth as number) ?? (initialContract.params?.groove_depth as number) ?? 0.5,
        lens_edge_thickness: (lens?.params?.lens_edge_thickness as number) ?? (initialContract.params?.lens_edge_thickness as number) ?? 2.0,
    });

    // Independent parameter states for Left and Right lenses
    const [leftParams, setLeftParams] = useState<LensParams>(() => extractParams(initialContract.left));
    const [rightParams, setRightParams] = useState<LensParams>(() => extractParams(initialContract.right));

    // Contour points for the currently selected eye
    const [points, setPoints] = useState<[number, number][]>([]);
    const [selectedPointIdx, setSelectedPointIdx] = useState<number | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const svgRef = useRef<SVGSVGElement>(null);

    // Sync active eye contour points on switch
    useEffect(() => {
        const lensData = selectedEye === 'L' ? initialContract.left : initialContract.right;
        if (lensData?.points_mm) {
            setPoints(lensData.points_mm);
            setSelectedPointIdx(null);
        }
    }, [selectedEye, initialContract]);

    // Convenient getters/setters for params. 'wall' is kept synchronized across both sides.
    const activeParams = selectedEye === 'L' ? leftParams : rightParams;
    const updateActiveParam = (key: keyof LensParams, value: number) => {
        if (key === 'wall') {
            setLeftParams((prev) => ({ ...prev, wall: value }));
            setRightParams((prev) => ({ ...prev, wall: value }));
        } else if (selectedEye === 'L') {
            setLeftParams((prev) => ({ ...prev, [key]: value }));
        } else {
            setRightParams((prev) => ({ ...prev, [key]: value }));
        }
    };

    const viewBox = useMemo(() => {
        if (!points || points.length === 0) return '-50 -50 100 100';
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        points.forEach(([x, y]) => {
            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
        });
        const pad = 15;
        return `${minX - pad} ${minY - pad} ${maxX - minX + pad * 2} ${maxY - minY + pad * 2}`;
    }, [points]);

    const pathD = useMemo(() => {
        if (!points || points.length === 0) return '';
        return points.reduce(
            (acc, [x, y], idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`,
            ''
        ) + ' Z';
    }, [points]);

    const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
        if (selectedPointIdx === null || !svgRef.current) return;
        const rect = svgRef.current.getBoundingClientRect();
        const svgX = e.clientX - rect.left;
        const svgY = e.clientY - rect.top;

        const viewBoxParts = viewBox.split(' ').map(Number);
        const scaleX = viewBoxParts[2] / rect.width;
        const scaleY = viewBoxParts[3] / rect.height;

        const newX = viewBoxParts[0] + svgX * scaleX;
        const newY = viewBoxParts[1] + svgY * scaleY;

        setPoints((prev) => {
            const updated = [...prev];
            updated[selectedPointIdx] = [newX, newY];
            return updated;
        });
    };

    const handleApplyChanges = async () => {
        setIsSubmitting(true);

        const currentLensPoints = points;
        const updatedContract: BuildContract = {
            ...initialContract,
            dbl_mm: dbl,
            params: {
                ...(initialContract.params || {}),
                wall: activeParams.wall,
            },
            left: {
                ...initialContract.left,
                points_mm: selectedEye === 'L' ? currentLensPoints : initialContract.left.points_mm,
                params: leftParams as unknown as Record<string, number>,
            },
            right: {
                ...initialContract.right,
                points_mm: selectedEye === 'R' ? currentLensPoints : initialContract.right.points_mm,
                params: rightParams as unknown as Record<string, number>,
            },
        };

        try {
            await onUpdateContract(updatedContract);
            onClose();
        } catch (error) {
            console.error('Failed to rebuild model:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) return null;

    const isLoading = isGenerating || isSubmitting;

    return (
        <div className="modal-backdrop" role="presentation">
            <section
                className="reference-modal"
                role="dialog"
                aria-modal="true"
                style={{ maxWidth: '480px', width: '90%', padding: '1.5rem', background: '#1a1a1a', color: '#fff', borderRadius: '12px' }}
            >
                <button
                    className="modal-close"
                    type="button"
                    onClick={onClose}
                    disabled={isLoading}
                    aria-label="Close editor"
                >
                    ×
                </button>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Tweak Frame Fit</h2>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            type="button"
                            className={`button ${selectedEye === 'L' ? 'button--primary' : 'button--secondary'}`}
                            onClick={() => setSelectedEye('L')}
                            disabled={isLoading}
                            style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
                        >
                            Left Lens
                        </button>
                        <button
                            type="button"
                            className={`button ${selectedEye === 'R' ? 'button--primary' : 'button--secondary'}`}
                            onClick={() => setSelectedEye('R')}
                            disabled={isLoading}
                            style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
                        >
                            Right Lens
                        </button>
                    </div>
                </div>

                {/* 2D Interactive Contour Viewer & Node Editor */}
                <div style={{ background: '#000', borderRadius: '6px', border: '1px solid #333', overflow: 'hidden', marginBottom: '1rem' }}>
                    <svg
                        ref={svgRef}
                        viewBox={viewBox}
                        style={{ width: '100%', height: '200px', cursor: selectedPointIdx !== null ? 'grabbing' : 'default' }}
                        onMouseMove={handleSvgMouseMove}
                        onMouseUp={() => setSelectedPointIdx(null)}
                        onMouseLeave={() => setSelectedPointIdx(null)}
                    >
                        <path d={pathD} fill="rgba(0, 150, 255, 0.15)" stroke="#0099ff" strokeWidth="0.8" />
                        {points.map(([x, y], idx) => (
                            <circle
                                key={idx}
                                cx={x}
                                cy={y}
                                r={selectedPointIdx === idx ? 2.5 : 1.5}
                                fill={selectedPointIdx === idx ? '#ffaa00' : '#ffffff'}
                                stroke="#0099ff"
                                strokeWidth="0.5"
                                style={{ cursor: 'pointer' }}
                                onMouseDown={(e) => {
                                    if (isLoading) return;
                                    e.stopPropagation();
                                    setSelectedPointIdx(idx);
                                }}
                            />
                        ))}
                    </svg>
                </div>

                {/* Parameter Sliders - Bound to Active Eye Parameters */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#0099ff', textTransform: 'uppercase', fontWeight: 'bold' }}>
                        Configuring: {selectedEye === 'L' ? 'Left Lens' : 'Right Lens'}
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Clearance / Buffer:</strong> {activeParams.clearance.toFixed(2)} mm
                        </label>
                        <input
                            type="range"
                            min="0.0"
                            max="0.8"
                            step="0.05"
                            value={activeParams.clearance}
                            disabled={isLoading}
                            onChange={(e) => updateActiveParam('clearance', parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Groove Depth (Inward Overlap):</strong> {activeParams.groove_depth.toFixed(2)} mm
                        </label>
                        <input
                            type="range"
                            min="0.2"
                            max="1.5"
                            step="0.05"
                            value={activeParams.groove_depth}
                            disabled={isLoading}
                            onChange={(e) => updateActiveParam('groove_depth', parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Groove Width (Lens Edge Height):</strong> {activeParams.lens_edge_thickness.toFixed(1)} mm
                        </label>
                        <input
                            type="range"
                            min="1.0"
                            max="5.0"
                            step="0.1"
                            value={activeParams.lens_edge_thickness}
                            disabled={isLoading}
                            onChange={(e) => updateActiveParam('lens_edge_thickness', parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>

                    <hr style={{ borderColor: '#333', margin: '0.25rem 0' }} />

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Frame Wall Thickness (Shared):</strong> {activeParams.wall.toFixed(1)} mm
                        </label>
                        <input
                            type="range"
                            min="1.5"
                            max="6.0"
                            step="0.5"
                            value={activeParams.wall}
                            disabled={isLoading}
                            onChange={(e) => updateActiveParam('wall', parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Bridge Width (DBL):</strong> {dbl.toFixed(1)} mm
                        </label>
                        <input
                            type="range"
                            min="10.0"
                            max="26.0"
                            step="0.5"
                            value={dbl}
                            disabled={isLoading}
                            onChange={(e) => setDbl(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>
                </div>

                <button
                    type="button"
                    className="button button--primary button--full"
                    onClick={() => void handleApplyChanges()}
                    disabled={isLoading}
                >
                    {isLoading ? 'Rebuilding Model…' : 'Apply & Rebuild 3D Frame'}
                </button>
            </section>
        </div>
    );
};