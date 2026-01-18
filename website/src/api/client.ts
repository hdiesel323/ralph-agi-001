/**
 * API client configuration for RALPH-AGI backend.
 */

import axios from 'axios';

// API base URL - defaults to localhost:8000 in development
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Axios instance configured for the RALPH-AGI API
 */
export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log errors in development
    if (import.meta.env.DEV) {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * WebSocket connection URL
 */
export const WS_URL = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws`;

export default apiClient;
