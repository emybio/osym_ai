// API Configuration for development and production

const isDevelopment = import.meta.env.DEV;

export const API_BASE_URL = isDevelopment
  ? 'http://localhost:8000'  // Test için localhost
  : window.location.origin;

export const API_BASE_PATH = '/api/v1';

export const createApiUrl = (endpoint) => {
  // endpoint already contains full URL
  if (endpoint.startsWith('http')) {
    return endpoint;
  }

  // Special fix for development port conflicts
  if (isDevelopment) {
    // Development: Force port 8000 and check if backend is running
    if (endpoint.startsWith('/api')) {
      return `http://localhost:8000${endpoint}`;
    }

    // endpoint is relative
    return `http://localhost:8000${API_BASE_PATH}${endpoint}`;
  }

  // endpoint already contains api path
  if (endpoint.startsWith('/api')) {
    return `${API_BASE_URL}${endpoint}`;
  }

  // endpoint is relative
  return `${API_BASE_URL}${API_BASE_PATH}${endpoint}`;
};

export const apiCall = async (endpoint, options = {}) => {
  const defaultOptions = {
    credentials: 'include',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'Content-Type': 'application/json',
    },
  };

  // Get CSRF token
  const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  };

  const csrftoken = getCookie('csrftoken');
  if (csrftoken && options.method !== 'GET' && options.method !== 'HEAD') {
    defaultOptions.headers['X-CSRFToken'] = csrftoken;
  }

  // Override content type for FormData
  if (options.body instanceof FormData) {
    delete defaultOptions.headers['Content-Type'];
  }

  const url = createApiUrl(endpoint);

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`API Error for ${url}:`, error);
    throw error;
  }
};