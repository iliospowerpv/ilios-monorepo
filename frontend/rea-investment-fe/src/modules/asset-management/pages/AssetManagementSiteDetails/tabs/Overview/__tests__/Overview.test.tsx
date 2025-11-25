import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiClient } from '../../../../../../../api';

import OverviewTab from '../Overview';

import responseStub from './detailedSiteInfoResponseStub.json';
import siteDetailsStub from './baseSiteDetailsResponseStub.json';

jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    assetManagement: {
      siteInfo: jest.fn()
    }
  }
}));

describe('OverviewTab component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();

    if (jest.isMockFunction(ApiClient.assetManagement.siteInfo)) {
      ApiClient.assetManagement.siteInfo.mockResolvedValue(responseStub);
    }

    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <OverviewTab siteDetails={siteDetailsStub as any} />
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(screen.getByText('Site Level Details')).toBeInTheDocument();
      expect(screen.getByText('EPC Contractor')).toBeInTheDocument();
    });

    const revealButton = screen.getByRole('button');
    fireEvent.click(revealButton);

    await waitFor(() => {
      expect(screen.getByText('12345678')).toBeInTheDocument();
    });
  });
});
