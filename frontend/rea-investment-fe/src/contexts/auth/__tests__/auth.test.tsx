import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../auth';

describe('AuthProvider', () => {
  it('provides auth-data for its child components', () => {
    const queryClient = new QueryClient();

    const { result } = renderHook(useAuth, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      )
    });

    expect(result.current).toEqual({
      isAuthPending: false,
      isAuthenticated: false,
      user: null
    });
  });
});
