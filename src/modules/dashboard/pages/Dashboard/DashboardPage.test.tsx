import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from './Dashboard';
import theme from '../../../../utils/styles/theme';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

jest.mock('../../components/TaskDashboardList/TaskDashboardList', () => ({
  __esModule: true,
  default: () => <div>TaskDashboardList-component-placeholder</div>
}));

jest.mock('../../components/NotificationList/NotificationList', () => ({
  __esModule: true,
  default: () => <div>NotificationList-component-placeholder</div>
}));

describe('DashboardPage', () => {
  const queryClient = new QueryClient();

  test('renders the Dashboard heading', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider theme={theme}>
            <DashboardPage />
          </ThemeProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );
    const heading = screen.getByText('Dashboard');
    expect(heading).toBeInTheDocument();
  });
});
