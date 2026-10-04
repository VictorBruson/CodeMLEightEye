const API_URL = import.meta.env.VITE_API_URL ?? '';
const FRAME_API_URL = import.meta.env.VITE_FRAME_API_URL ?? '';

export interface MeasureResponse {
  contract: Record<string, unknown>;
  overlays: {
    left: string;
    right: string;
  };
  measurements: {
    left: { A_mm: number; B_mm: number };
    right: { A_mm: number; B_mm: number };
  };
}

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

export async function measurePair(left: Blob, right: Blob): Promise<MeasureResponse> {
  const formData = new FormData();
  formData.append('left', left, 'left-lens.jpg');
  formData.append('right', right, 'right-lens.jpg');
  formData.append('dbl_mm', '18');
  formData.append('params', '{}');
  formData.append('left_flipped', 'false');
  formData.append('right_flipped', 'false');

  const response = await fetch(`${API_URL}/api/measure`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new Error(body?.detail?.message ?? 'The lens images could not be measured.');
  }
  return response.json() as Promise<MeasureResponse>;
}

export async function generateFrame(contract: Record<string, unknown>): Promise<FrameApiResponse> {
  const response = await fetch(`${FRAME_API_URL}/frame`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(contract),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new Error(body?.error?.message ?? 'The frame could not be generated.');
  }
  return response.json() as Promise<FrameApiResponse>;
}
