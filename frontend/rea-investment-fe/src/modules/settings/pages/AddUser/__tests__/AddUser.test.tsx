import { screen, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AddUserPage } from '../AddUser';

jest.mock('react-router-dom', () => ({
  useNavigate: jest.fn()
}));

jest.mock('../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn(() => jest.fn())
}));

jest.mock('../../../../../api', () => ({
  ApiClient: {
    companies: {
      sites: jest.fn(() =>
        Promise.resolve(
          JSON.parse(`{
        "data": [
          {
            "id": 1,
            "name": "Nvidia Corporation",
            "sites": [
              {
                "id": 1,
                "name": "Apollo"
              },
              {
                "id": 2,
                "name": "Jupiter"
              },
              {
                "id": 3,
                "name": "Merkury"
              }
            ]
          },
          {
            "id": 3,
            "name": "Google inc.",
            "sites": [
              {
                "id": 7,
                "name": "Saturn"
              },
              {
                "id": 8,
                "name": "Neptune"
              },
            ]
          }
        ]
      }`)
        )
      ),
      rolesWithCompanyType: jest.fn(() =>
        Promise.resolve(
          JSON.parse(`{
        "data": [
          {
            "company_type": "O&M Contractor",
            "role": {
              "id": 112,
              "name": "Operations Manager"
            }
          },
          {
            "company_type": "Project/Site Owner",
            "role": {
              "id": 115,
              "name": "Diligence Manager"
            }
          },
          {
            "company_type": "Project/Site Owner",
            "role": {
              "id": 116,
              "name": "Legal Specialist"
            }
          },
          {
            "company_type": "Project/Site Owner",
            "role": {
              "id": 122,
              "name": "System Admin"
            }
          },
          {
            "company_type": "Project/Site Owner",
            "role": {
              "id": 123,
              "name": "Executive"
            }
          }
        ]
      }`)
        )
      ),
      contractors: jest.fn(() =>
        Promise.resolve(
          JSON.parse(`{
        "skip": 0,
        "limit": 10,
        "total": 5,
        "items": [
          {
            "name": "4 Paws LLC",
            "email": "happy@doggy.com",
            "phone": "135178062869",
            "address": "238 Happy Hollow",
            "company_type": "Project/Site Owner",
            "id": 6
          },
          {
            "name": "Holly Molly",
            "email": "user@molly.com",
            "phone": "18486204000",
            "address": "833 Church Hill Road, Augusta, ME",
            "company_type": "Project/Site Owner",
            "id": 9
          },
          {
            "name": "Green Lantern",
            "email": "user@example.com",
            "phone": "14084862000",
            "address": "719 Main Street Solar",
            "company_type": "O&M Contractor",
            "id": 16
          }
        ]
      }`)
        )
      )
    }
  }
}));

const mock = function () {
  return {
    observe: jest.fn(),
    disconnect: jest.fn()
  };
};

// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
global.ResizeObserver = mock;

describe('AddUser page', () => {
  it('should render form correctly', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AddUserPage />
      </QueryClientProvider>
    );

    expect(screen.getByText('First Name')).toBeInTheDocument();
    expect(screen.getByText('Last Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Company')).toBeInTheDocument();
    expect(screen.getByText('Role')).toBeInTheDocument();
    expect(screen.getByText('Project Access')).toBeInTheDocument();
  });
});
