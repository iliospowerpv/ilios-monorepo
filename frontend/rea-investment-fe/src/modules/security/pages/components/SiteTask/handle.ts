import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../../handles';
import { createLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../../utils/breadcrumbs';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createLoader>>>;

export const createHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (
      typeof data?.siteData?.id !== 'number' ||
      typeof data?.companyData?.id !== 'number' ||
      typeof data?.taskDetails?.id !== 'number' ||
      typeof data?.board?.id !== 'number'
    ) {
      return [];
    }
    const siteDetails = queryClient.getQueryData<LoaderOutput['siteData']>([
      'site',
      'crumbs',
      'O&M (Production Monitoring)',
      { siteId: data.siteData.id }
    ]);
    const companyDetails = queryClient.getQueryData<LoaderOutput['companyData']>([
      'company',
      'crumbs',
      'O&M (Production Monitoring)',
      { companyId: data.companyData.id }
    ]);

    const taskDetails = queryClient.getQueryData<LoaderOutput['taskDetails']>([
      'tasks',
      'details',
      { boardId: data.board.id, taskId: data.taskDetails.id }
    ]);

    return siteDetails && companyDetails && taskDetails
      ? [
          { title: BREADCRUMB_LABELS.OM, link: '/operations-and-maintenance' },
          { title: companyDetails.name, link: `/operations-and-maintenance/companies/${companyDetails.id}` },
          {
            title: siteDetails.name,
            link: CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB(siteDetails.id, 'om')
          },
          { title: taskDetails.external_id }
        ]
      : [{ title: BREADCRUMB_LABELS.OM, link: '/operations-and-maintenance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'operations-and-maintenance'
  });
};
