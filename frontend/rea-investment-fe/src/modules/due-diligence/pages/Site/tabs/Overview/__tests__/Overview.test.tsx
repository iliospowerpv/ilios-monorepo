import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Overview from '../Overview';
import { NotificationsProvider } from '../../../../../../../contexts/notifications/notifications';
import type { SiteDetailedInfo, CompanyDetails } from '../../../../../../../api';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

jest.mock('../components/CoTerminusChecksPanel/CoTerminusChecksPanel', () => ({
  __esModule: true,
  default: () => <div>CoTerminusChecksPanel-placeholder</div>
}));

const mockedSite: SiteDetailedInfo = {
  name: "John's test site 1",
  address: 'Av. dos Andradas, 3000',
  city: 'Belo Horizonte',
  state: 'IL',
  county: 'MG',
  zip_code: '30260',
  system_size_ac: 6,
  system_size_dc: 88,
  das: 'Mana Monitoring System',
  lon_lat_url: '17,15',
  id: 371,
  company: {
    name: "John's test company",
    email: 'John@test.us',
    phone: '6019521325',
    address: '1600 Amphitheatre Parkway',
    company_type: 'O&M Contractor',
    id: 182
  },
  account: 'DAS account',
  username: 'DAS username',
  password: '12345678',
  cameras_uuids: []
};

const mockedCompany: CompanyDetails = {
  name: "John's test company",
  email: 'John@test.us',
  phone: '6019521325',
  address: '1600 Amphitheatre Parkway',
  company_type: 'O&M Contractor',
  id: 182,
  total_sites: 1,
  sites_placed_in_service: 1,
  sites_under_construction: 0,
  total_capacity: 6
};

describe('Overview tab component', () => {
  const queryClient = new QueryClient();

  test('renders the component', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <Overview siteDetails={mockedSite} companyDetails={mockedCompany} />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('overview-tab__component')).toBeInTheDocument();
    expect(screen.getByText('CoTerminusChecksPanel-placeholder')).toBeInTheDocument();
  });
});
