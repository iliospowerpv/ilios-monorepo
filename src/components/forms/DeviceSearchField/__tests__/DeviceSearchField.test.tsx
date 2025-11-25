import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DeviceSearchField } from '../DeviceSearchField';
import { ApiClient } from '../../../../api';

const siteDevicesMock = JSON.parse(`
  {
    "items": [
        {
            "id": 380,
            "name": "Network gateway"
        },
        {
            "id": 385,
            "name": "Camera"
        },
        {
            "id": 477,
            "name": "New test meter device"
        },
        {
            "id": 540,
            "name": "Inverter"
        }
    ]
  }
`);

jest.mock('../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../../../../api', () => ({
  ApiClient: {
    taskManagement: {
      siteDevice: jest.fn()
    }
  }
}));

describe('DeviceSearchField component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();
    const onChangeMockFn = jest.fn();
    const selectedDeviceMock = {
      id: 477,
      name: 'New test meter device'
    };

    if (jest.isMockFunction(ApiClient.taskManagement.siteDevice)) {
      ApiClient.taskManagement.siteDevice.mockImplementation((...args: [number, { search: string }]) => {
        const [, params] = args;
        const { search } = params;

        if (!search) {
          return Promise.resolve(siteDevicesMock);
        } else {
          const filteredBySearchTerm = siteDevicesMock.items.filter((item: { name: string }) =>
            item.name.includes(search)
          );
          return Promise.resolve({ items: filteredBySearchTerm });
        }
      });
    }

    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <DeviceSearchField value={selectedDeviceMock} siteId={5} onChange={onChangeMockFn} />
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(ApiClient.taskManagement.siteDevice).toHaveBeenCalledTimes(2);
      expect(ApiClient.taskManagement.siteDevice).toHaveBeenLastCalledWith(5, { search: '' });
    });

    const searchInput = screen.getByRole('combobox');
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveValue('New test meter device');

    const openBtn = screen.getByLabelText('Open');
    fireEvent.click(openBtn);

    await waitFor(() => {
      const deviceOption = screen.getByText('Network gateway');
      expect(deviceOption).toBeInTheDocument();
      fireEvent.click(deviceOption);
    });

    await waitFor(() => {
      expect(onChangeMockFn).toHaveBeenCalledTimes(1);
      expect(onChangeMockFn.mock.calls[0][1]).toEqual({ id: 380, name: 'Network gateway' });
    });
  });
});
