import { apiCall } from '../config/api';

class OfflineManager {
  constructor() {
    this.offlineQueue = [];
    this.isOnline = navigator.onLine;
    this.setupEventListeners();
  }

  setupEventListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processOfflineQueue();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  // Add request to offline queue
  addToOfflineQueue(request) {
    this.offlineQueue.push({
      ...request,
      timestamp: Date.now(),
      id: Math.random().toString(36).substr(2, 9)
    });

    // Store in localStorage for persistence
    localStorage.setItem('offlineQueue', JSON.stringify(this.offlineQueue));
  }

  // Process offline queue when back online
  async processOfflineQueue() {
    if (this.offlineQueue.length === 0) return;

    console.log(`Processing ${this.offlineQueue.length} offline requests`);

    const queue = [...this.offlineQueue];
    this.offlineQueue = [];
    localStorage.removeItem('offlineQueue');

    for (const request of queue) {
      try {
        await this.replayRequest(request);
        console.log('Successfully replayed request:', request.id);
      } catch (error) {
        console.error('Failed to replay request:', request.id, error);
        // Add back to queue if failed
        this.offlineQueue.push(request);
      }
    }

    if (this.offlineQueue.length > 0) {
      localStorage.setItem('offlineQueue', JSON.stringify(this.offlineQueue));
    }
  }

  // Replay a stored request
  async replayRequest(storedRequest) {
    const { url, method = 'GET', headers, body } = storedRequest;

    return fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      body
    });
  }

  // Enhanced API call with offline support
  async apiCallOffline(endpoint, options = {}) {
    const url = `/api/quiz${endpoint}`;

    if (!this.isOnline && ['POST', 'PUT', 'DELETE'].includes(options.method || 'GET')) {
      // Store POST/PUT/DELETE requests for later
      this.addToOfflineQueue({
        url,
        ...options
      });

      // Return optimistic response for certain endpoints
      if (endpoint === '/quicktest/save/') {
        return {
          success: true,
          message: 'Test sonuçlarınız internet bağlantısı geldiğinde gönderilecek',
          offline: true
        };
      }

      throw new Error('Çevrimdışısınız. İşleminiz bağlantı geldiğinde gerçekleştirilecek.');
    }

    try {
      const response = await apiCall(endpoint, options);

      // Cache GET requests for offline access
      if ((options.method || 'GET') === 'GET' && response) {
        this.cacheResponse(url, response);
      }

      return response;
    } catch (error) {
      // Try to get cached response if offline
      if (!this.isOnline) {
        const cachedResponse = await this.getCachedResponse(url);
        if (cachedResponse) {
          return {
            ...cachedResponse,
            cached: true,
            message: 'Önbelleğe alınmış veriler gösteriliyor'
          };
        }
      }

      throw error;
    }
  }

  // Cache response
  async cacheResponse(url, data) {
    try {
      const cache = await caches.open('osym-ai-api-v1');
      const response = new Response(JSON.stringify(data), {
        headers: {
          'Content-Type': 'application/json',
          'X-Cached': 'true'
        }
      });
      await cache.put(url, response);
    } catch (error) {
      console.error('Error caching response:', error);
    }
  }

  // Get cached response
  async getCachedResponse(url) {
    try {
      const cache = await caches.open('osym-ai-api-v1');
      const response = await cache.match(url);
      if (response) {
        const data = await response.json();
        return data;
      }
    } catch (error) {
      console.error('Error getting cached response:', error);
    }
    return null;
  }

  // Cache questions for offline tests
  async cacheQuestions(subject, questions) {
    const cacheKey = `questions_${subject}`;
    localStorage.setItem(cacheKey, JSON.stringify({
      questions,
      timestamp: Date.now(),
      expiresAt: Date.now() + (24 * 60 * 60 * 1000) // 24 hours
    }));
  }

  // Get cached questions
  getCachedQuestions(subject) {
    const cacheKey = `questions_${subject}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
      try {
        const data = JSON.parse(cached);
        if (data.expiresAt > Date.now()) {
          return data.questions;
        } else {
          // Expired, remove from cache
          localStorage.removeItem(cacheKey);
        }
      } catch (error) {
        console.error('Error parsing cached questions:', error);
        localStorage.removeItem(cacheKey);
      }
    }

    return null;
  }

  // Sync test results when online
  async syncTestResults(results) {
    if (!this.isOnline) {
      localStorage.setItem('pendingTestResults', JSON.stringify(results));
      return { success: true, offline: true };
    }

    try {
      const response = await apiCall('/quicktest/save/', {
        method: 'POST',
        body: JSON.stringify(results)
      });

      localStorage.removeItem('pendingTestResults');
      return response;
    } catch (error) {
      // Store for later sync
      localStorage.setItem('pendingTestResults', JSON.stringify(results));
      throw error;
    }
  }

  // Get pending test results
  getPendingTestResults() {
    const pending = localStorage.getItem('pendingTestResults');
    return pending ? JSON.parse(pending) : null;
  }

  // Clear all cached data
  async clearCache() {
    try {
      // Clear localStorage caches
      const keys = Object.keys(localStorage).filter(key =>
        key.startsWith('questions_') ||
        key === 'pendingTestResults' ||
        key === 'offlineQueue'
      );
      keys.forEach(key => localStorage.removeItem(key));

      // Clear caches
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
      );

      return { success: true };
    } catch (error) {
      console.error('Error clearing cache:', error);
      return { success: false, error };
    }
  }

  // Get cache status
  async getCacheStatus() {
    try {
      const cacheNames = await caches.keys();
      let totalSize = 0;

      for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const requests = await cache.keys();
        totalSize += requests.length;
      }

      const storage = await navigator.storage.estimate();

      return {
        cachesCount: cacheNames.length,
        cachedItems: totalSize,
        storageUsed: storage.usage,
        storageQuota: storage.quota,
        localStorageItems: keys.length
      };
    } catch (error) {
      console.error('Error getting cache status:', error);
      return null;
    }
  }
}

// Create singleton instance
const offlineManager = new OfflineManager();

export default offlineManager;