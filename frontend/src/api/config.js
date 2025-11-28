// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper functions
export const getApiUrl = (endpoint) => {
  if (endpoint.startsWith('http')) {
    return endpoint;
  }
  // Remove leading slash if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export const apiCall = async (endpoint, options = {}) => {
  const url = getApiUrl(endpoint);

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed for ${endpoint}:`, error);
    throw error;
  }
};
