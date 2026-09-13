import {
  HealthResponse,
  RunCreateRequest,
  RunCreateResponse,
  RunStatusResponse,
  LeadSummary,
  LeadDetail,
} from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  };

  try {
    const response = await fetch(url, { ...options, headers });
    let data: any;

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        typeof data === 'object' && data?.detail
          ? data.detail
          : `HTTP ${response.status}: ${response.statusText}`;
      throw new ApiError(errorMessage, response.status, data);
    }

    return data as T;
  } catch (error: any) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error.message || 'Network request failed. Unable to reach backend API.',
      0
    );
  }
}

export const apiClient = {
  getHealth: (): Promise<HealthResponse> => request<HealthResponse>('/api/health'),

  createRun: (payload: RunCreateRequest = {}): Promise<RunCreateResponse> =>
    request<RunCreateResponse>('/api/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getRuns: (): Promise<RunStatusResponse[]> => request<RunStatusResponse[]>('/api/runs'),

  getRun: (runId: string): Promise<RunStatusResponse> =>
    request<RunStatusResponse>(`/api/runs/${encodeURIComponent(runId)}`),

  getRunLeads: (runId: string): Promise<LeadSummary[]> =>
    request<LeadSummary[]>(`/api/runs/${encodeURIComponent(runId)}/leads`),

  getLeads: (): Promise<LeadSummary[]> => request<LeadSummary[]>('/api/leads'),

  getLead: (leadId: string): Promise<LeadDetail> =>
    request<LeadDetail>(`/api/leads/${encodeURIComponent(leadId)}`),
};
