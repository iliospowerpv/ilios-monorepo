import React from 'react';
import { screen, render, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AlertsTab from '../Alerts';

// Capture the props handed to BaseTable so we can drive the server-side
// datasource directly and exercise the column cell renderers (the Resolve
// action lives inside the "Actions" column renderer).
const mockBaseTableProps = jest.fn();
const mockGridApi = {
  showNoRowsOverlay: jest.fn(),
  hideOverlay: jest.fn(),
  refreshServerSide: jest.fn()
};

jest.mock('../../../../../../../components/common/tables/BaseTable/BaseTable', () => ({
  __esModule: true,
  default: require('react').forwardRef((props: any, ref: any) => {
    const react = require('react');
    mockBaseTableProps(props);
    react.useImperativeHandle(ref, () => ({ getApi: () => mockGridApi }));
    const sampleRow = {
      id: 7,
      device_id: 42,
      is_resolved: false,
      type: 'Underperformance',
      severity: 'warning',
      error_message: 'Output below threshold',
      alert_start: '2026-06-15T13:00:00'
    };
    return react.createElement(
      'div',
      { 'data-testid': 'base-table' },
      (props.columnDefs || []).map((col: any, i: number) =>
        col.cellRenderer
          ? react.createElement('div', { key: i }, col.cellRenderer({ data: sampleRow }))
          : null
      )
    );
  })
}));

// ConfirmationModal: render a confirm trigger only while open so the resolve
// flow can be completed in the test.
jest.mock('../../../../../../../components/modals/ConfirmationModal/ConfirmationModal', () => ({
  __esModule: true,
  default: ({ open, onConfirm }: { open: boolean; onConfirm: () => void }) =>
    open
      ? require('react').createElement(
          'button',
          { 'data-testid': 'confirm-resolve', onClick: onConfirm },
          'confirm'
        )
      : null
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

// Isolate the custom theme key the component reads; MUI's own components fall
// back to the default theme for styling.
jest.mock('@mui/material/styles', () => {
  const actual = jest.requireActual('@mui/material/styles');
  return {
    ...actual,
    useTheme: () => ({ alertSeverity: { severe: '#5F1513', warning: '#F4D918', high: '#B02E0C' } })
  };
});

const mockDeviceAlerts = jest.fn();
const mockCompanyAlertResolve = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    operationsAndMaintenance: {
      deviceAlerts: (...args: unknown[]) => mockDeviceAlerts(...args),
      companyAlertResolve: (...args: unknown[]) => mockCompanyAlertResolve(...args)
    }
  }
}));

const renderTab = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AlertsTab deviceDetails={{} as any} deviceId={42} siteId={4} companyId={1} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  mockBaseTableProps.mockReset();
  mockNotify.mockReset();
  mockDeviceAlerts.mockReset();
  mockCompanyAlertResolve.mockReset();
  mockGridApi.showNoRowsOverlay.mockReset();
  mockGridApi.hideOverlay.mockReset();
  mockGridApi.refreshServerSide.mockReset();
});

describe('PH Device Details Alerts tab', () => {
  it('renders a server-side BaseTable', () => {
    mockDeviceAlerts.mockResolvedValue({ items: [], total: 0 });
    renderTab();
    expect(screen.getByTestId('base-table')).toBeInTheDocument();
    const props = mockBaseTableProps.mock.calls[0][0];
    expect(props.rowModelType).toBe('serverSide');
    expect(props.serverSideDatasource).toBeDefined();
  });

  it('queries device alerts for the route deviceId, unresolved only, with paging', async () => {
    mockDeviceAlerts.mockResolvedValue({ items: [{ id: 7 }], total: 1 });
    renderTab();
    const props = mockBaseTableProps.mock.calls[0][0];
    const params = {
      request: { startRow: 0, endRow: 25, sortModel: [] },
      success: jest.fn(),
      fail: jest.fn()
    };
    props.serverSideDatasource.getRows(params);
    await waitFor(() => expect(mockDeviceAlerts).toHaveBeenCalledTimes(1));
    expect(mockDeviceAlerts).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ skip: 0, limit: 25, is_resolved: false })
    );
    await waitFor(() => expect(params.success).toHaveBeenCalledWith({ rowData: [{ id: 7 }], rowCount: 1 }));
  });

  it('shows the no-rows overlay and never fabricates rows when empty', async () => {
    mockDeviceAlerts.mockResolvedValue({ items: [], total: 0 });
    renderTab();
    const props = mockBaseTableProps.mock.calls[0][0];
    const params = {
      request: { startRow: 0, endRow: 25, sortModel: [] },
      success: jest.fn(),
      fail: jest.fn()
    };
    props.serverSideDatasource.getRows(params);
    await waitFor(() => expect(mockGridApi.showNoRowsOverlay).toHaveBeenCalled());
    expect(params.success).toHaveBeenCalledWith({ rowData: [], rowCount: 0 });
  });

  it('resolves an alert through the confirmation modal', async () => {
    mockDeviceAlerts.mockResolvedValue({ items: [{ id: 7 }], total: 1 });
    mockCompanyAlertResolve.mockResolvedValue({ message: 'Alert resolved', code: 200 });
    renderTab();

    fireEvent.click(screen.getByRole('button', { name: 'Resolve' }));
    fireEvent.click(await screen.findByTestId('confirm-resolve'));

    await waitFor(() => expect(mockCompanyAlertResolve).toHaveBeenCalledWith(7));
    await waitFor(() => expect(mockNotify).toHaveBeenCalledWith('Alert resolved'));
  });
});
