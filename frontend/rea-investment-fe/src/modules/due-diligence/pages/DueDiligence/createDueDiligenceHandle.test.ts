import { RouteHandle } from '../../../../handles';
import createDueDiligenceHandle from './handle';

jest.mock('../../../../handles', () => ({
  RouteHandle: {
    createHandle: jest.fn()
  }
}));

describe('createDueDiligenceHandle', () => {
  it('creates a handle with the correct properties', () => {
    const mockCreateHandle = jest.fn().mockReturnValue('mockHandle');
    RouteHandle.createHandle = mockCreateHandle;

    const result = createDueDiligenceHandle();

    expect(mockCreateHandle).toHaveBeenCalledTimes(1);

    expect(mockCreateHandle).toHaveBeenCalledWith({
      moduleId: 'due-diligence',
      crumbsBuilder: expect.any(Function)
    });

    expect(result).toBe('mockHandle');

    const crumbsBuilder = mockCreateHandle.mock.calls[0][0].crumbsBuilder;
    expect(crumbsBuilder()).toEqual([{ title: 'Diligence' }]);
  });
});
