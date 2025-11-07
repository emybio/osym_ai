const API_URL = "http://127.0.0.1:8000";

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

class ApiClient {
  constructor(baseURL = API_URL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    console.log('=== API REQUEST DEBUG ===');
    console.log('Base URL:', this.baseURL);
    console.log('Endpoint:', endpoint);
    console.log('Full URL:', url);
    console.log('Method:', options.method || 'GET');
    console.log('Headers:', config.headers);
    console.log('Body:', options.body);

    try {
      console.log('Sending request...');
      const response = await fetch(url, config);
      console.log('Response received. Status:', response.status);
      console.log('Response headers:', response.headers);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('API Error:', errorData);
        throw new ApiError(
          errorData.detail || errorData.error || `HTTP ${response.status}`,
          response.status,
          errorData
        );
      }

      const data = await response.json();
      console.log('API Response data:', data);
      return data;
    } catch (error) {
      console.error('API Request failed:', error);
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Network error occurred', 0, { originalError: error.message });
    }
  }

  // Question API methods
  async getQuestions() {
    return this.request('/api/v1/questions/');
  }

  async generateQuestion(params) {
    return this.request('/api/v1/questions/generate/', {
      method: 'POST',
      body: JSON.stringify({
        subject: params.subject || 'Matematik',
        topic: params.topic || 'Temel Kavramlar',
        difficulty: params.difficulty || 'Orta',
        provider: params.provider || 'openai',
      }),
    });
  }

  async explainQuestion(questionId, provider = null) {
    return this.request(`/api/v1/questions/${questionId}/explain/`, {
      method: 'POST',
      body: JSON.stringify({
        provider: provider,  // Backend'de null olursa sorunun source'unu kullanır
      }),
    });
  }

  // User progress API methods (placeholder for future implementation)
  async getUserStats() {
    return this.request('/api/v1/user/stats/');
  }

  async getRecentExams() {
    return this.request('/api/v1/user/exams/');
  }

  // Subject API methods (placeholder for future implementation)
  async getSubjects() {
    return this.request('/api/v1/subjects/');
  }

  async getSubjectProgress(subjectId) {
    return this.request(`/api/v1/subjects/${subjectId}/progress/`);
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export convenience methods
export const questionService = {
  getAll: () => apiClient.getQuestions(),
  generate: (params) => apiClient.generateQuestion(params),
  explain: (questionId, provider = null) => apiClient.explainQuestion(questionId, provider),
};

export const userService = {
  getStats: () => apiClient.getUserStats(),
  getRecentExams: () => apiClient.getRecentExams(),
};

export const subjectService = {
  getAll: () => apiClient.getSubjects(),
  getProgress: (subjectId) => apiClient.getSubjectProgress(subjectId),
};

export { ApiError };
export default apiClient;