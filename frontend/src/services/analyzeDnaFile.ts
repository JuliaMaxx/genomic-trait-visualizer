import { API_BASE_URL } from '../config/env';

export async function analyzeDnaFile(file: File | null): Promise<Trait[]> {
  if (!file) {
    throw new Error('No file provided');
  }

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/analyze/`, {
    method: 'POST',
    body: formData,
  });

  // TODO: use AbortController to handle request cancellation

  // TODO: handle network errors and other unexpected issues here

  if (!response.ok) {
    // TODO: improve error hanling here
    throw new Error(`Request failed with status ${response.status}.`);
  }

  return response.json();
}
