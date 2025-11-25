import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiClient, User } from '../../api';

interface Auth {
  isAuthenticated: boolean;
  isAuthPending: boolean;
  user: User | null;
}

const AuthContext = React.createContext<Auth | undefined>(undefined);

export type { User };

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const queryClient = useQueryClient();

  const [token, setToken] = React.useState<string | null>(ApiClient._tokenManager.getAuthToken());

  const { isLoading: isUserDataLoading, data: userData } = useQuery({
    enabled: !!token,
    queryFn: ApiClient.user.me,
    queryKey: ['user']
  });

  const onTokenChange = React.useCallback(
    (token: string | null) => {
      setToken(token);
      queryClient.clear();
    },
    [queryClient, setToken]
  );

  React.useEffect(() => {
    ApiClient._tokenManager.subscribe(onTokenChange);

    return () => ApiClient._tokenManager.unsubscribe(onTokenChange);
  }, [onTokenChange]);

  const value = React.useMemo<Auth>(
    () => ({
      isAuthenticated: !!userData,
      isAuthPending: isUserDataLoading,
      user: userData || null
    }),
    [userData, isUserDataLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): Auth => {
  const context = React.useContext(AuthContext);

  if (context === undefined) throw new Error('AuthContext is available only within the scope of AuthProvider');

  return context;
};
