import React, { useState, useEffect, useMemo, useRef } from 'react';

export interface ContractLens {
    eye: 'L' | 'R';
    points_mm: [number, number][];
    flipped?: boolean;
    [key: string]: unknown;
}

export interface BuildContract {
    left: ContractLens;
    right: ContractLens;
    dbl_mm: number;
    params?: Record<string, number>;
    [key: string]: unknown;
}

interface LensEditorProps {
    isOpen: boolean;
    onClose: () => void;
    initialContract: BuildContract;
    onUpdateContract: (updatedContract: BuildContract) => void;
    isGenerating?: boolean;
}

export const LensEditor: React.FC<LensEditorProps> = ({
                                                          isOpen,
                                                          onClose,
                                                          initialContract,
                                                          onUpdateContract,
                                                          isGenerating = false,
                                                      }) => {
    const [clearance, setClearance] = useState<number>(
        (initialContract.params?.clearance as number) ?? 0.2
    );
    const [wall, setWall] = useState<number>(
        (initialContract.params?.wall as number) ?? 3.0
    );
    const [dbl, setDbl] = useState<number>(initialContract.dbl_mm ?? 18);

    const [selectedEye, setSelectedEye] = useState<'L' | 'R'>('L');
    const [points, setPoints] = useState<[number, number][]>([]);
    const [selectedPointIdx, setSelectedPointIdx] = useState<number | null>(null);

    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        const lensData = selectedEye === 'L' ? initialContract.left : initialContract.right;
        if (lensData?.points_mm) {
            setPoints(lensData.points_mm);
            setSelectedPointIdx(null);
        }
    }, [selectedEye, initialContract]);

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

    const handleApplyChanges = () => {
        const updatedContract: BuildContract = {
            ...initialContract,
            dbl_mm: dbl,
            params: {
                ...(initialContract.params || {}),
                clearance,
                wall,
            },
            [selectedEye === 'L' ? 'left' : 'right']: {
                ...(selectedEye === 'L' ? initialContract.left : initialContract.right),
                points_mm: points,
            },
        };
        onUpdateContract(updatedContract);
        onClose();
    };

    if (!isOpen) return null;

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
                            style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
                        >
                            Left Lens
                        </button>
                        <button
                            type="button"
                            className={`button ${selectedEye === 'R' ? 'button--primary' : 'button--secondary'}`}
                            onClick={() => setSelectedEye('R')}
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
                                    e.stopPropagation();
                                    setSelectedPointIdx(idx);
                                }}
                            />
                        ))}
                    </svg>
                </div>

                {/* Parameter Sliders */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Clearance / Buffer:</strong> {clearance.toFixed(2)} mm
                        </label>
                        <input
                            type="range"
                            min="0.0"
                            max="0.8"
                            step="0.05"
                            value={clearance}
                            onChange={(e) => setClearance(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <small style={{ color: '#aaa' }}>Increase if physical lens is too big for the printed rim[cite: 4, 6].</small>
                    </div>

                    <div>
                        <label style={{ display: 'block', marginBottom: '0.25rem' }}>
                            <strong>Frame Wall Thickness:</strong> {wall.toFixed(1)} mm
                        </label>
                        <input
                            type="range"
                            min="1.5"
                            max="6.0"
                            step="0.5"
                            value={wall}
                            onChange={(e) => setWall(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <small style={{ color: '#aaa' }}>Controls overall rim width surrounding the lens cutout[cite: 4, 6].</small>
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
                            onChange={(e) => setDbl(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <small style={{ color: '#aaa' }}>Distance between inner nasal lens edges[cite: 1, 2].</small>
                    </div>
                </div>

                <button
                    type="button"
                    className="button button--primary button--full"
                    onClick={handleApplyChanges}
                    disabled={isGenerating}
                >
                    {isGenerating ? 'Rebuilding Model…' : 'Apply & Rebuild 3D Frame'}
                </button>
            </section>
        </div>
    );
};