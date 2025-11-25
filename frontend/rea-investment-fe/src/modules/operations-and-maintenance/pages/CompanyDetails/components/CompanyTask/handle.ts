import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../../../handles';
import { createLoader } from './loader';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createLoader>>>;

export const createHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (
      typeof data?.companyDetails?.id !== 'number' ||
      typeof data?.taskDetails?.id !== 'number' ||
      typeof data?.board?.id !== 'number'
    ) {
      return [];
    }
    const companyDetails = queryClient.getQueryData<LoaderOutput['companyDetails']>([
      'company',
      'crumbs',
      'O&M (Production Monitoring)',
      { companyId: data.companyDetails.id }
    ]);

    const taskDetails = queryClient.getQueryData<LoaderOutput['taskDetails']>([
      'tasks',
      'details',
      { boardId: data.board.id, taskId: data.taskDetails.id }
    ]);

    return companyDetails && taskDetails
      ? [
          { title: 'O&M', link: '/operations-and-maintenance' },
          { title: companyDetails.name, link: `/operations-and-maintenance/companies/${companyDetails.id}` },
          { title: taskDetails.external_id }
        ]
      : [{ title: 'O&M', link: '/operations-and-maintenance' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'operations-and-maintenance'
  });
};
