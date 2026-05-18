import { API_BASE_URL } from '../config/env';
import type {
  RsidCatalogItem,
  RsidDetail,
  SearchResponse,
  TraitDefinition,
  TraitDetail,
  TraitResult,
} from '../types/analysis';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

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

export function fetchTraitCatalog() {
  return getJson<TraitDefinition[]>('/traits/');
}

export function fetchTraitDetail(traitId: string) {
  return getJson<TraitDetail>(`/traits/${traitId}/detail`);
}

export function fetchRsidCatalog() {
  return getJson<RsidCatalogItem[]>('/rsids/');
}

export function fetchRsidDetail(rsid: string) {
  return getJson<RsidDetail>(`/rsids/${rsid}`);
}

export function searchCatalog(query: string) {
  const params = new URLSearchParams({ q: query });
  return getJson<SearchResponse>(`/search/?${params.toString()}`);
}
