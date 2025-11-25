import { renderHook } from '@testing-library/react';
import { NotificationsProvider, useNotify } from '../notifications';
import * as Toastify from 'react-toastify';

jest.mock('react-toastify', () => ({
  ToastContainer: () => <div>ToastContainer</div>,
  toast: jest.fn(),
  Zoom: null
}));

describe('NotificationsProvider', () => {
  it('provides notify function to let child components trigger toast notifications', () => {
    const { result } = renderHook(useNotify, {
      wrapper: ({ children }) => <NotificationsProvider>{children}</NotificationsProvider>
    });
    const notify = result.current;

    notify('Success toast');

    expect(Toastify.toast).toHaveBeenCalledTimes(1);
  });
});
