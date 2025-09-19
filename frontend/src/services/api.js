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
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('arxivbot_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API service methods
export const apiService = {
  // Authentication
  login: async (username, password) => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },

  refreshToken: async () => {
    const response = await api.post('/auth/refresh');
    return response.data;
  },

  // Enhanced v2.4 Search
  searchV24: async (searchParams) => {
    const response = await api.post('/api/v2/search', searchParams);
    return response.data;
  },

  // Legacy v2.0 Search (for compatibility)
  searchV20: async (query, k = 20) => {
    const response = await api.get('/search', { 
      params: { q: query, k } 
    });
    return response.data;
  },

  // Paper details
  getPaper: async (paperId) => {
    const response = await api.get(`/paper/${paperId}`);
    return response.data;
  },

  // Download paper
  downloadPaper: async (paperId) => {
    const response = await api.get(`/download/${paperId}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Enhanced v2.4 Feedback
  submitFeedbackV24: async (feedback) => {
    const response = await api.post('/api/v2/feedback', feedback);
    return response.data;
  },

  // Legacy v2.0 Feedback
  submitFeedbackV20: async (paperId, value) => {
    const response = await api.post('/feedback', {
      paper_id: paperId,
      value: value
    });
    return response.data;
  },

  // GPT-4o Summarization
  summarizePapers: async (paperIds, summaryType = 'detailed', queryContext = null) => {
    const response = await api.post('/api/v2/summarize', {
      paper_ids: paperIds,
      summary_type: summaryType,
      query_context: queryContext
    });
    return response.data;
  },

  // System statistics
  getStatsV24: async () => {
    const response = await api.get('/api/v2/stats');
    return response.data;
  },

  getStatsV20: async () => {
    const response = await api.get('/stats');
    return response.data;
  },

  // Health check
  getHealthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Discovery & acquisition bridge
  discoverPapers: async (query, maxResults = 20) => {
    const response = await api.post('/discovery/query', { query, max_results: maxResults });
    return response.data;
  },

  acquirePaper: async (paper) => {
    const response = await api.post('/acquisition/acquire', { paper });
    return response.data;
  },

  runMaintenance: async () => {
    const response = await api.post('/maintenance/run');
    return response.data;
  },

  getCollectionSummary: async () => {
    const response = await api.get('/collection/summary');
    return response.data;
  },

  getDuplicates: async () => {
    const response = await api.get('/organization/duplicates');
    return response.data;
  },

  getMetrics: async () => {
    const response = await api.get('/metrics');
    return response.data;
  },
};

// v2.4 Specific helpers
export const searchHelpers = {
  // Build search request for v2.4 API
  buildSearchRequest: (params) => {
    const {
      query,
      maxResults = 20,
      sources = [],
      minScore = 0.0,
      publishedAfter = null,
      publishedBefore = null,
      categories = [],
      enableCitationExpansion = true,
      citationDepth = 1,
      summaryType = 'detailed'
    } = params;

    return {
      q: query,
      k: maxResults,
      sources: sources.length > 0 ? sources : undefined,
      min_score: minScore,
      published_after: publishedAfter,
      published_before: publishedBefore,
      categories: categories.length > 0 ? categories : undefined,
      enable_citation_expansion: enableCitationExpansion,
      citation_depth: citationDepth,
      summary_type: summaryType
    };
  },

  // Parse search results with enhanced information
  parseSearchResults: (response) => {
    const {
      query,
      total_results,
      results,
      search_time_ms,
      sources_searched,
      citation_expansion,
      aggregations,
      v2_4_features
    } = response;

    return {
      query,
      totalResults: total_results,
      results: results.map(result => ({
        id: result.id,
        externalId: result.external_id,
        title: result.title,
        authors: result.authors,
        source: result.source,
        year: result.year,
        abstract: result.abstract,
        pdfUrl: result.pdf_url,
        categories: result.categories || [],
        doi: result.doi,
        venue: result.venue,
        citationCount: result.citation_count || 0,
        score: result.score,
        confidence: result.confidence,
        summary: result.summary,
        scoringDetails: result.scoring_details || {},
        published: result.published,
        createdAt: result.created_at,
        updatedAt: result.updated_at
      })),
      searchTimeMs: search_time_ms,
      sourcesSearched: sources_searched || [],
      citationExpansion: citation_expansion || {},
      aggregations: aggregations || {},
      hasV24Features: v2_4_features || false
    };
  }
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

  isAuthError: (error) => {
    return error.response?.status === 401;
  },

  isServerError: (error) => {
    return error.response?.status >= 500;
  }
};

export default api;
