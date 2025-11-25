import { RouteHandle } from '../handles';

describe('route-handles', () => {
  it('builds a list of crumb-partials using a builder-function mapped to the route', () => {
    const handle = RouteHandle.createHandle({
      crumbsBuilder: () => [{ title: 'Settings', link: '/settings' }, { title: 'Add User' }]
    });
    const breadcrumbs = handle.buildCrumbs({});

    expect(breadcrumbs).toEqual([{ title: 'Settings', link: '/settings' }, { title: 'Add User' }]);
  });
});
