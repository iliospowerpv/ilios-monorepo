import { RouteHandle } from '../../../../handles';
import createDashboardHandle from './handle';

jest.mock('../../../../handles', () => ({
  RouteHandle: {
    createHandle: jest.fn()
  }
}));

describe('createDashboardHandle', () => {
  it('creates a handle with the correct properties', () => {
    const mockCreateHandle = jest.fn().mockReturnValue('mockHandle');
    RouteHandle.createHandle = mockCreateHandle;

    const result = createDashboardHandle();

    expect(mockCreateHandle).toHaveBeenCalledTimes(1);

    expect(mockCreateHandle).toHaveBeenCalledWith({
      moduleId: 'dashboard',
      crumbsBuilder: expect.any(Function)
    });

    expect(result).toBe('mockHandle');

    const crumbsBuilder = mockCreateHandle.mock.calls[0][0].crumbsBuilder;
    expect(crumbsBuilder()).toEqual([{ title: 'Dashboard' }]);
  });
});
