import { render, screen, waitFor } from '@testing-library/react';
import SignUpPage from '../SignUp';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useLocation: () => ({
    search: '?email=curtis.weaver@example.com&token=fbibfiwbfewfiwebifewhif'
  })
}));

jest.mock('../screens', () => ({
  SignUpFormScreen: () => <div>Sign-up form</div>,
  BlankScreen: () => <div>Blank screen</div>,
  SignUpSuccesScreen: () => <div>Sign-up sucess</div>,
  SignUpFailedScreen: () => <div>Sign-up failed</div>
}));

jest.mock('../../../api', () => ({
  ApiClient: {
    user: {
      validateEmailToken: () => new Promise(resolve => setTimeout(resolve, 1000)),
      setupPassword: () => Promise.resolve()
    }
  }
}));

describe('SignUpPage', () => {
  it('should render component correctly', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SignUpPage />
      </QueryClientProvider>
    );
    const currentScreen = screen.getByText('Blank screen');
    expect(currentScreen).toBeInTheDocument();

    await waitFor(
      () => {
        expect(currentScreen).not.toBeInTheDocument();
        const updatedScreen = screen.getByText('Sign-up form');
        expect(updatedScreen).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });
});
