const API_URL = import.meta.env.VITE_API_URL ?? '';

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
