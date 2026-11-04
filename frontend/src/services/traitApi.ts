import { API_BASE_URL } from '../config/env';
import type {
  RsidCatalogItem,
  RsidDetail,
  SearchResponse,
  TraitAnalysisDetail,
  TraitAnalysisSummary,
  TraitCatalogDetail,
  TraitCatalogSummary,
} from '../types/api';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

async function postFile<T>(
  path: string,
  file: File,
  signal?: AbortSignal,
): Promise<T> {
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

export function analyzeDnaFile(file: File, signal?: AbortSignal) {
  return postFile<TraitAnalysisSummary[]>('/analyze/', file, signal);
}

export function evaluateTrait(
  traitId: string,
  file: File,
  signal?: AbortSignal,
) {
  return postFile<TraitAnalysisDetail>(
    `/traits/${traitId}/evaluate`,
    file,
    signal,
  );
}

export function fetchTraitCatalog(signal?: AbortSignal) {
  return getJson<TraitCatalogSummary[]>('/traits/', signal);
}

export function fetchTraitDetail(traitId: string, signal?: AbortSignal) {
  return getJson<TraitCatalogDetail>(`/traits/${traitId}`, signal);
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
