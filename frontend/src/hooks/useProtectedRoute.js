import { useAuth } from "../contexts/AuthContext";

export const useProtectedRoute = (requireAdmin = false) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  // auth henüz yüklenmediyse
  const authNotLoaded = (isAuthenticated === undefined);

  return {
    canAccess: !authNotLoaded && !loading && isAuthenticated && (!requireAdmin || isAdmin),
    isChecking: authNotLoaded || loading,
    reason:
      authNotLoaded || loading
        ? "Checking..."
        : !isAuthenticated
        ? "Not authenticated"
        : requireAdmin && !isAdmin
        ? "Not authorized"
        : null,
  };
};
