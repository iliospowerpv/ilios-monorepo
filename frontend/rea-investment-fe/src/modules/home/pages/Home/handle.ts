import { RouteHandle } from '../../../../handles/handles';

export const createHomeHandle = () =>
  RouteHandle.createHandle({
    crumbsBuilder: () => [{ title: 'Home' }]
  });
