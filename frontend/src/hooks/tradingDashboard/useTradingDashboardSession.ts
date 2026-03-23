import { useEffect, useState } from "react";
import { fetchMe, login } from "../../services/api";
import { useTradingStore } from "../../store/useTradingStore";
import { RefreshOptions, getErrorMessage } from "./shared";

interface TradingDashboardSessionOptions {
  tradeStatusFilter?: string;
  refreshUserData: (options?: RefreshOptions) => Promise<void>;
  onAuthFailure: (message?: string) => void;
  onAuthSuccess: () => void;
}

export const useTradingDashboardSession = ({
  tradeStatusFilter,
  refreshUserData,
  onAuthFailure,
  onAuthSuccess
}: TradingDashboardSessionOptions) => {
  const { accessToken, currentUser, setSession } = useTradingStore();
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isBootstrappingSession, setIsBootstrappingSession] = useState(Boolean(accessToken));

  const clearAuthError = () => {
    setAuthError(null);
  };

  useEffect(() => {
    if (!accessToken || currentUser !== null) {
      setIsBootstrappingSession(false);
      return;
    }

    let isMounted = true;
    const controller = new AbortController();

    const bootstrapSession = async () => {
      setIsBootstrappingSession(true);
      try {
        const user = await fetchMe(accessToken, controller.signal);
        if (!isMounted) {
          return;
        }
        setSession(
          {
            access_token: accessToken,
            refresh_token: useTradingStore.getState().refreshToken,
            token_type: "bearer"
          },
          user
        );
        onAuthSuccess();
        clearAuthError();
        await refreshUserData({
          includeAssignments: true,
          includeOverview: true,
          includeTrades: true,
          tradeStatus: tradeStatusFilter,
          token: accessToken,
          signal: controller.signal
        });
      } catch (loadError) {
        if (isMounted && !controller.signal.aborted) {
          const message = getErrorMessage(loadError, "Session expiree. Reconnecte-toi.");
          setAuthError(message);
          onAuthFailure(message);
        }
      } finally {
        if (isMounted) {
          setIsBootstrappingSession(false);
        }
      }
    };

    void bootstrapSession();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [accessToken, currentUser, onAuthFailure, onAuthSuccess, refreshUserData, setSession, tradeStatusFilter]);

  const handleLogin = async (username: string, password: string) => {
    setIsAuthenticating(true);
    clearAuthError();
    try {
      const tokens = await login(username, password);
      const user = await fetchMe(tokens.access_token);
      setSession(tokens, user);
      onAuthSuccess();
      await refreshUserData({
        includeAssignments: true,
        includeOverview: true,
        includeTrades: true,
        tradeStatus: tradeStatusFilter,
        token: tokens.access_token
      });
    } catch (loginError) {
      setAuthError(getErrorMessage(loginError, "Connexion impossible."));
    } finally {
      setIsAuthenticating(false);
      setIsBootstrappingSession(false);
    }
  };

  return {
    authError,
    clearAuthError,
    isAuthenticating,
    isBootstrappingSession,
    handleLogin
  };
};
