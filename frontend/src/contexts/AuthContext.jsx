import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};

// ============================
//  FETCH WITH TIMEOUT
// ============================
const fetchWithTimeout = (url, options, timeout = 2500) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Timeout")), timeout)
    )
  ]);
};

export const AuthProvider = ({ children }) => {

  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ============================
  // CSRF TOKEN FETCH
  // ============================
  const getCSRFToken = async () => {
    try {
      // Django'nun CSRF token'ını direkt olarak al
      const res = await fetch("http://localhost:8000/api/v1/auth/csrf/", {
        credentials: "include",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        }
      });

      if (!res.ok) throw new Error("CSRF alınamadı");

      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) return null;

      const data = await res.json();
      return data.csrfToken;
    } catch (err) {
      console.warn("CSRF alınamadı:", err);
      return null;
    }
  };

  // ============================
  //   API CALL — STABLE
  // ============================
  const apiCall = async (url, options = {}) => {
    const defaultOptions = {
      credentials: "include",
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    };

    const finalOptions = { ...defaultOptions, ...options };

    // CSRF gerekiyorsa
    if (["POST", "PUT", "PATCH", "DELETE"].includes(finalOptions.method?.toUpperCase())) {
      const csrf = await getCSRFToken();
      if (csrf) finalOptions.headers["X-CSRFToken"] = csrf;
    }

    let response;
    try {
      response = await fetchWithTimeout(url, finalOptions, 2500);
    } catch (err) {
      throw new Error("API timeout veya network hatası");
    }

    const contentType = response.headers.get("content-type") || "";

    // JSON değil → backend HTML hata sayfası döndürmüş
    if (!contentType.includes("application/json")) {
      const raw = await response.text().catch(() => "");
      console.warn("API JSON yerine HTML döndürdü:", raw.slice(0, 200));
      throw new Error("Sunucu JSON yerine HTML döndürdü");
    }

    // JSON parse
    let json;
    try {
      json = await response.json();
    } catch (err) {
      throw new Error("JSON parse edilemedi");
    }

    if (!response.ok) {
      throw new Error(json.error || `HTTP ${response.status}`);
    }

    return json;
  };

  // ============================
  //   CHECK AUTH STATUS
  // ============================
  const checkAuthStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiCall("http://localhost:8000/api/v1/auth/check/");

      setUser(data.user);
      setIsAuthenticated(data.authenticated);
      setIsAdmin(data.is_admin);
      setError(null);
    } catch (err) {
      console.warn("Auth check FAILED:", err.message);

      setUser(null);
      setIsAuthenticated(false);
      setIsAdmin(false);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // ============================
  // LOGIN
  // ============================
  const login = async (username, password) => {
    try {
      setLoading(true);
      const data = await apiCall("http://localhost:8000/api/v1/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      setUser(data.user);
      setIsAuthenticated(true);
      setIsAdmin(data.user.is_staff);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // ============================
  // LOGOUT
  // ============================
  const logout = async (callback) => {
    try {
      await apiCall("http://localhost:8000/api/v1/auth/logout/", { method: "POST" });
    } catch (err) {
      console.warn("Logout error:", err);
    }

    setUser(null);
    setIsAuthenticated(false);
    setIsAdmin(false);

    if (callback) callback();
  };

  // ============================
  // CONTEXT VALUE
  // ============================
  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isAdmin,
      loading,
      error,
      login,
      logout,
      checkAuthStatus
    }}>
      {children}
    </AuthContext.Provider>
  );
};
