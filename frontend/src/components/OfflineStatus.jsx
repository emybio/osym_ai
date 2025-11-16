import React, { useState, useEffect } from 'react';
import { usePWA } from '../hooks/usePWA';
import offlineManager from '../utils/offlineApi';

const OfflineStatus = () => {
  const { isOnline, isInstallable, installApp, requestNotificationPermission, showNotification } = usePWA();
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [cacheStatus, setCacheStatus] = useState(null);
  const [pendingOperations, setPendingOperations] = useState(0);

  useEffect(() => {
    // Check notification permission
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
    }

    // Load pending operations
    const updatePendingOperations = () => {
      const queue = localStorage.getItem('offlineQueue');
      const pendingResults = localStorage.getItem('pendingTestResults');
      const count = (queue ? JSON.parse(queue).length : 0) + (pendingResults ? 1 : 0);
      setPendingOperations(count);
    };

    updatePendingOperations();
    window.addEventListener('storage', updatePendingOperations);

    return () => {
      window.removeEventListener('storage', updatePendingOperations);
    };
  }, []);

  useEffect(() => {
    // Show install prompt after some delay
    if (isInstallable && !isOnline) {
      const timer = setTimeout(() => {
        setShowInstallPrompt(true);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isInstallable, isOnline]);

  const handleInstall = async () => {
    const success = await installApp();
    if (success) {
      setShowInstallPrompt(false);
    }
  };

  const handleEnableNotifications = async () => {
    const granted = await requestNotificationPermission();
    if (granted) {
      setNotificationPermission('granted');
      showNotification('Bildirimler aktif!', {
        body: 'Artık önemli güncellemelerden bildirim alacaksınız.',
        icon: '/icon-192x192.png'
      });
    }
  };

  const getCacheStatus = async () => {
    const status = await offlineManager.getCacheStatus();
    setCacheStatus(status);
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      {/* Offline Indicator */}
      {!isOnline && (
        <div className="bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3">
          <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
          <div>
            <p className="font-semibold">Çevrimdışısınız</p>
            <p className="text-sm opacity-90">İnternet bağlantısı bekleniyor...</p>
          </div>
        </div>
      )}

      {/* Pending Operations */}
      {pendingOperations > 0 && (
        <div className="bg-orange-500 text-white px-4 py-3 rounded-lg shadow-lg">
          <p className="font-semibold">Bekleyen İşlemler</p>
          <p className="text-sm opacity-90">{pendingOperations} işlem bağlantı geldiğinde gönderilecek</p>
        </div>
      )}

      {/* Install Prompt */}
      {showInstallPrompt && (
        <div className="bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">Uygulamayı Yükleyin</p>
          <p className="text-sm mb-3">Çevrimdışı erişim ve daha iyi performans için uygulamayı yükleyin.</p>
          <div className="flex space-x-2">
            <button
              onClick={handleInstall}
              className="bg-white text-blue-600 px-3 py-1 rounded text-sm font-medium hover:bg-blue-50 transition-colors"
            >
              Yükle
            </button>
            <button
              onClick={() => setShowInstallPrompt(false)}
              className="bg-blue-700 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-800 transition-colors"
            >
              Şimdi değil
            </button>
          </div>
        </div>
      )}

      {/* Notification Permission Request */}
      {isOnline && notificationPermission === 'default' && (
        <div className="bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">Bildirimleri Aktif Edin</p>
          <p className="text-sm mb-3">Önemli güncellemeler ve hatırlatıcılar için bildirimlere izin verin.</p>
          <div className="flex space-x-2">
            <button
              onClick={handleEnableNotifications}
              className="bg-white text-green-600 px-3 py-1 rounded text-sm font-medium hover:bg-green-50 transition-colors"
            >
              Aktif Et
            </button>
            <button
              onClick={() => setNotificationPermission('denied')}
              className="bg-green-700 text-white px-3 py-1 rounded text-sm font-medium hover:bg-green-800 transition-colors"
            >
              Hayır
            </button>
          </div>
        </div>
      )}

      {/* Cache Info Toggle */}
      {isOnline && (
        <button
          onClick={getCacheStatus}
          className="bg-gray-700 text-white px-3 py-2 rounded-lg shadow hover:bg-gray-800 transition-colors text-sm"
          title="Önbellek durumunu göster"
        >
          💾 Önbellek Bilgisi
        </button>
      )}

      {/* Cache Status Modal */}
      {cacheStatus && (
        <div className="bg-gray-800 text-white p-4 rounded-lg shadow-lg">
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-semibold">Önbellek Durumu</h3>
            <button
              onClick={() => setCacheStatus(null)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Önbellek Sayısı:</span>
              <span>{cacheStatus.cachesCount}</span>
            </div>
            <div className="flex justify-between">
              <span>Önbelleklenmiş Öğe:</span>
              <span>{cacheStatus.cachedItems}</span>
            </div>
            <div className="flex justify-between">
              <span>Depolama Kullanımı:</span>
              <span>{formatBytes(cacheStatus.storageUsed)}</span>
            </div>
            <div className="flex justify-between">
              <span>Toplam Kota:</span>
              <span>{formatBytes(cacheStatus.storageQuota)}</span>
            </div>
            <div className="flex justify-between">
              <span>Local Storage:</span>
              <span>{cacheStatus.localStorageItems} öğe</span>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-700">
            <button
              onClick={async () => {
                if (confirm('Tüm önbelleği temizlemek istediğinizden emin misiniz?')) {
                  await offlineManager.clearCache();
                  setCacheStatus(null);
                  alert('Önbellek temizlendi.');
                }
              }}
              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
            >
              Önbelleği Temizle
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default OfflineStatus;