import { RouteHandle } from '../../../../handles';

describe('RouteHandle', () => {
  it('should return the correct moduleId for a given route', () => {
    const handle = RouteHandle.createHandle({
      moduleId: 'asset-management',
      crumbsBuilder: () => []
    });

    expect(handle.getModuleId()).toBe('asset-management');
  });

  it('should return an empty array for crumbs if no crumbsBuilder is found', () => {
    const handle = RouteHandle.createHandle({});

    expect(handle.getModuleId()).toBeNull();
    expect(handle.buildCrumbs({})).toEqual([]);
  });
});
