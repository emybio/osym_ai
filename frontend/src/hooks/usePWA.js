import { useState, useEffect, useCallback } from 'react';

export const usePWA = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [swRegistration, setSwRegistration] = useState(null);

  // Initialize PWA
  useEffect(() => {
    // Check if app is already installed
    const checkInstalled = () => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const isInWebAppiOS = (window.navigator.standalone === true);
      const isInWebAppChrome = (window.matchMedia('(display-mode: standalone)').matches);
      setIsInstalled(isStandalone || isInWebAppiOS || isInWebAppChrome);
    };

    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(registration => {
          console.log('Service Worker registered:', registration);
          setSwRegistration(registration);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });
    }

    // Listen for beforeinstallprompt event
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setIsInstallable(true);
    };

    // Listen for appinstalled event
    const handleAppInstalled = () => {
      setIsInstallable(false);
      setIsInstalled(true);
      setDeferredPrompt(null);
    };

    // Check connection status
    const updateOnlineStatus = () => {
      setIsOnline(navigator.onLine);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    checkInstalled();
    updateOnlineStatus();

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
    };
  }, []);

  // Install PWA
  const installApp = useCallback(async () => {
    if (!deferredPrompt) {
      console.log('Install prompt not available');
      return false;
    }

    try {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === 'accepted') {
        console.log('User accepted the install prompt');
        setDeferredPrompt(null);
        setIsInstallable(false);
        return true;
      } else {
        console.log('User dismissed the install prompt');
        return false;
      }
    } catch (error) {
      console.error('Error during install:', error);
      return false;
    }
  }, [deferredPrompt]);

  // Request notification permission
  const requestNotificationPermission = useCallback(async () => {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      return true;
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }

    return false;
  }, []);

  // Subscribe to push notifications
  const subscribeToNotifications = useCallback(async () => {
    if (!swRegistration) {
      console.log('Service Worker not registered');
      return null;
    }

    try {
      const subscription = await swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.REACT_APP_VAPID_PUBLIC_KEY
      });

      console.log('Push subscription:', subscription);
      return subscription;
    } catch (error) {
      console.error('Error subscribing to push notifications:', error);
      return null;
    }
  }, [swRegistration]);

  // Cache data for offline use
  const cacheData = useCallback(async (url, data) => {
    if ('caches' in window) {
      try {
        const cache = await caches.open('osym-ai-data-v1');
        const response = new Response(JSON.stringify(data), {
          headers: {
            'Content-Type': 'application/json'
          }
        });
        await cache.put(url, response);
        console.log('Data cached successfully:', url);
      } catch (error) {
        console.error('Error caching data:', error);
      }
    }
  }, []);

  // Get cached data
  const getCachedData = useCallback(async (url) => {
    if ('caches' in window) {
      try {
        const cache = await caches.open('osym-ai-data-v1');
        const response = await cache.match(url);
        if (response) {
          const data = await response.json();
          console.log('Found cached data:', url);
          return data;
        }
      } catch (error) {
        console.error('Error getting cached data:', error);
      }
    }
    return null;
  }, []);

  // Sync data when online
  const syncWhenOnline = useCallback(async (syncFunction) => {
    if (navigator.onLine) {
      try {
        await syncFunction();
        console.log('Data synced successfully');
      } catch (error) {
        console.error('Error syncing data:', error);
      }
    } else if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      // Register background sync
      try {
        await swRegistration?.sync.register('background-sync');
        console.log('Background sync registered');
      } catch (error) {
        console.error('Error registering background sync:', error);
      }
    } else {
      // Fallback: Store in localStorage for later sync
      console.log('Offline: Data will be synced when online');
      // You can store the sync function or data in localStorage here
    }
  }, [swRegistration]);

  // Show notification
  const showNotification = useCallback((title, options = {}) => {
    if ('serviceWorker' in navigator && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        swRegistration?.showNotification(title, {
          icon: '/icon-192x192.png',
          badge: '/badge-72x72.png',
          vibrate: [100, 50, 100],
          ...options
        });
      }
    } else if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        icon: '/icon-192x192.png',
        ...options
      });
    }
  }, [swRegistration]);

  // Get storage info
  const getStorageInfo = useCallback(async () => {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        const estimate = await navigator.storage.estimate();
        return {
          quota: estimate.quota,
          usage: estimate.usage,
          usagePercentage: ((estimate.usage / estimate.quota) * 100).toFixed(2),
          available: estimate.quota - estimate.usage
        };
      } catch (error) {
        console.error('Error getting storage info:', error);
      }
    }
    return null;
  }, []);

  return {
    isOnline,
    isInstallable,
    isInstalled,
    installApp,
    requestNotificationPermission,
    subscribeToNotifications,
    cacheData,
    getCachedData,
    syncWhenOnline,
    showNotification,
    getStorageInfo,
    swRegistration
  };
};