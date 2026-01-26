import { RouteHandle } from '../../../../handles';

export const createPortfolioPageHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'portfolio',
    crumbsBuilder: () => [{ title: 'Portfolio' }]
  });
};

export default createPortfolioPageHandle;
