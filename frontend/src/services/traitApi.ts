import { API_BASE_URL } from '../config/env';
import type {
  RsidCatalogItem,
  RsidDetail,
  SearchResponse,
  TraitDefinition,
  TraitDetail,
  TraitResult,
} from '../types/analysis';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

async function postFile<T>(
  path: string,
  file: File | null,
  signal?: AbortSignal,
): Promise<T> {
  if (!file) {
    throw new Error('No DNA file selected.');
  }

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

export function analyzeDnaFile(file: File | null, signal?: AbortSignal) {
  return postFile<TraitResult[]>('/analyze/', file, signal);
}

export function evaluateTrait(
  traitId: string,
  file: File | null,
  signal?: AbortSignal,
) {
  return postFile<TraitDetail>(`/traits/${traitId}/evaluate`, file, signal);
}

export function fetchTraitCatalog(signal?: AbortSignal) {
  return getJson<TraitDefinition[]>('/traits/', signal);
}

export function fetchTraitDetail(traitId: string, signal?: AbortSignal) {
  return getJson<TraitDetail>(`/traits/${traitId}/detail`, signal);
}

export function fetchRsidCatalog(signal?: AbortSignal) {
  return getJson<RsidCatalogItem[]>('/rsids/', signal);
}

export function fetchRsidDetail(rsid: string, signal?: AbortSignal) {
  return getJson<RsidDetail>(`/rsids/${rsid}`, signal);
}

export function searchCatalog(query: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query });
  return getJson<SearchResponse>(`/search/?${params.toString()}`, signal);
}
