import { RouteHandle } from '../../../../handles';
import { BREADCRUMB_LABELS } from '../../../../utils/breadcrumbs';

export const createPortfolioPageHandle = () => {
  return RouteHandle.createHandle({
    moduleId: 'portfolio',
    crumbsBuilder: () => [{ title: BREADCRUMB_LABELS.PORTFOLIO }]
  });
};

export default createPortfolioPageHandle;
