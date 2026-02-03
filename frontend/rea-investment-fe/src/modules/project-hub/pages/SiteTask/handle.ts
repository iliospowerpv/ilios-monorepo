import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createLoader>>>;

export const createHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (
      typeof data?.siteData?.id !== 'number' ||
      typeof data?.taskDetails?.id !== 'number' ||
      typeof data?.board?.id !== 'number'
    ) {
      return [];
    }
    const siteDetails = queryClient.getQueryData<LoaderOutput['siteData']>([
      'site',
      'details',
      { siteId: data.siteData.id }
    ]);

    const taskDetails = queryClient.getQueryData<LoaderOutput['taskDetails']>([
      'tasks',
      'details',
      { boardId: data.board.id, taskId: data.taskDetails.id }
    ]);

    return siteDetails && taskDetails
      ? [
          { title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB },
          { title: siteDetails.name, link: CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB(siteDetails.id, 'tasks') },
          { title: taskDetails.external_id }
        ]
      : [{ title: BREADCRUMB_LABELS.PROJECT_HUB, link: CANONICAL_ROUTES.PROJECT_HUB }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
