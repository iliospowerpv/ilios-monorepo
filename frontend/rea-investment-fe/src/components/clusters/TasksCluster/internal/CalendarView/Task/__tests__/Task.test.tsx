import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import theme from '../../../../../../../utils/styles/theme';

import Task from '../Task';

describe('CalendarView Task component', () => {
  test('renders without crashing', () => {
    const eventInfo = {
      event: {
        id: '1',
        title: 'Test title',
        start: '2024-07-07',
        allDay: true,
        extendedProps: {
          description: 'Some description',
          priority: 'High',
          due_date: '2024-07-07',
          id: '1',
          externalId: 'TG-11',
          creator: 'John',
          assignee: null,
          status: 'Not Started'
        }
      }
    };

    render(
      <ThemeProvider theme={theme}>
        <Task eventInfo={eventInfo} />
      </ThemeProvider>
    );

    expect(screen.getByTestId('calendar-view__task')).toBeInTheDocument();
  });
});
