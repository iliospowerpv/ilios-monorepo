import { RouteHandle } from '../../../../handles';

export const createPortfolioPageHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'my-portfolio',
    crumbsBuilder: () => [{ title: 'My Portfolio' }]
  });
};

export default createPortfolioPageHandle;
