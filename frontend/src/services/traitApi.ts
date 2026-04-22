import { API_BASE_URL } from '../config/env';
import type { TraitDetail, TraitResult } from '../types/analysis';

async function postFile<T>(path: string, file: File | null): Promise<T> {
  if (!file) {
    throw new Error('No DNA file selected.');
  }

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

export function analyzeDnaFile(file: File | null) {
  return postFile<TraitResult[]>('/analyze/', file);
}

export function evaluateTrait(traitId: string, file: File | null) {
  return postFile<TraitDetail>(`/traits/${traitId}/evaluate`, file);
}
