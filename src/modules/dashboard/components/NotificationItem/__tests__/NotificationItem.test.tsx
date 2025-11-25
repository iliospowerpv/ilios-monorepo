import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import NotificationItem from '../NotificationItem';
import { NotificationsProvider } from '../../../../../contexts/notifications/notifications';

dayjs.extend(utc);

describe('Notification Item component', () => {
  const queryClient = new QueryClient();

  test('renders the component', () => {
    const notification = {
      id: 57,
      seen: false,
      kind: 'task_assignee_unset',
      created_at: '2024-08-01T08:43:18.919903',
      task: {
        id: 30,
        external_id: 'TG-30'
      },
      site: {
        id: 7,
        name: 'Demo Site 3'
      },
      company: {
        id: 2,
        name: 'Demo Company C'
      },
      actor: {
        id: 185,
        first_name: 'John',
        last_name: 'Smith'
      },
      extra: {}
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <NotificationItem notification={notification} loadMore={true} />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('notification-item__component')).toBeInTheDocument();
  });
});
