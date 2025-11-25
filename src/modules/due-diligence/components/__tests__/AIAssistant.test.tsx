import React from 'react';
import { render, screen, act, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, useMatches, useBlocker } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@testing-library/jest-dom';
import AIAssistant from '../AIAssistant';
import { RouteHandle } from '../../../../handles';
import { ApiClient } from '../../../../api';
import useWebSocket from 'react-use-websocket';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useBlocker: jest.fn(),
  useMatches: jest.fn()
}));

jest.mock('../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      getChatBotSession: jest.fn()
    }
  }
}));

jest.mock('react-use-websocket', () => ({
  __esModule: true,
  default: jest.fn(),
  ReadyState: {}
}));

describe('AIAssistant', () => {
  it('renders and functions correctly', async () => {
    if (jest.isMockFunction(useMatches)) {
      const handle = RouteHandle.createHandle({
        moduleId: 'due-diligence',
        crumbsBuilder: () => [],
        enabledFeatures: {
          ['ai-assistant']: { generateConfig: (data: any) => ({ siteId: data?.siteId, enabled: true }) }
        }
      });
      const data = { siteId: 5 };
      useMatches.mockReturnValue([{ handle, data }]);
    }

    if (jest.isMockFunction(useBlocker)) {
      useBlocker.mockReturnValue({});
    }

    if (jest.isMockFunction(ApiClient.dueDiligence.getChatBotSession)) {
      ApiClient.dueDiligence.getChatBotSession.mockImplementation(() =>
        Promise.resolve({
          token: {
            access_token:
              'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJjb21wYW55X2lkIjoxODIsInNpdGVfaWQiOjM3MSwiZXhwIjoxNzM0NjIyMjQ3fQ.Nc0qd7Es38RTG0vmdbtJe7vMtG4Yj-98u7tsbFzQLbc',
            token_type: 'bearer'
          },
          session_id: '12fee3d2-9f5d-56bf-8273-ae3b69a26ffb'
        })
      );
    }

    if (jest.isMockFunction(useWebSocket)) {
      useWebSocket.mockReturnValue({});
    }

    const queryClient = new QueryClient();

    await act(() =>
      render(
        <BrowserRouter>
          <QueryClientProvider client={queryClient}>
            <AIAssistant />
          </QueryClientProvider>
        </BrowserRouter>
      )
    );

    const openChatbotButton = screen.getByTestId('ai-chatbot_open-btn');
    fireEvent.click(openChatbotButton);

    await waitFor(() => {
      const closeConversationBtn = screen.getByTestId('ai-chatbot_close-conversation-btn');
      fireEvent.click(closeConversationBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Close this chat?')).toBeInTheDocument();
    });

    await waitFor(() => {
      const confirmationDialogConfirm = screen.getByText('Confirm');
      fireEvent.click(confirmationDialogConfirm);
    });

    await waitFor(() => {
      expect(screen.getByText('AI Assistant')).not.toBeVisible();
    });

    fireEvent.click(openChatbotButton);

    await waitFor(() => {
      const resetConversationBtn = screen.getByTestId('ai-chatbot_reset-conversation-btn');
      fireEvent.click(resetConversationBtn);
    });

    await waitFor(() => {
      const confirmationDialogConfirm = screen.getByText('Confirm');
      fireEvent.click(confirmationDialogConfirm);
    });

    expect(screen.getByText('AI Assistant')).toBeVisible();

    await waitFor(() => {
      const collapseChatbotBtn = screen.getByTestId('ai-chatbot_collapse-btn');
      fireEvent.click(collapseChatbotBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('AI Assistant')).not.toBeVisible();
    });
  });
});
