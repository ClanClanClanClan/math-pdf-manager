import axios from 'axios';

// Base API configuration
export const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add timestamp to avoid caching issues
    config.params = {
      ...config.params,
      _t: Date.now()
    };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// API service methods — only includes endpoints that exist on the backend
export const apiService = {
  // Health check
  getHealthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Discovery & acquisition
  discoverPapers: async (query, maxResults = 20) => {
    const response = await api.post('/discovery/query', { query, max_results: maxResults });
    return response.data;
  },

  acquirePaper: async (paper) => {
    const response = await api.post('/acquisition/acquire', { paper });
    return response.data;
  },

  // Maintenance
  runMaintenance: async () => {
    const response = await api.post('/maintenance/run');
    return response.data;
  },

  // Collection
  getCollectionSummary: async () => {
    const response = await api.get('/collection/summary');
    return response.data;
  },

  getDuplicates: async () => {
    const response = await api.get('/organization/duplicates');
    return response.data;
  },

  // Metrics
  getMetrics: async () => {
    const response = await api.get('/metrics');
    return response.data;
  },
};

// Error handling helpers
export const errorHelpers = {
  getErrorMessage: (error) => {
    if (error.response) {
      // Server responded with error status
      return error.response.data?.detail ||
             error.response.data?.message ||
             `Server error: ${error.response.status}`;
    } else if (error.request) {
      // Request was made but no response received
      return 'No response from server. Please check your connection.';
    } else {
      // Something else happened
      return error.message || 'An unexpected error occurred';
    }
  },

  isNetworkError: (error) => {
    return !error.response && error.request;
  },

  isServerError: (error) => {
    return error.response?.status >= 500;
  }
};

export default api;
