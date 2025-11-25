import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
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
      'details',
      { companyId: data.companyDetails.id }
    ]);

    const taskDetails = queryClient.getQueryData<LoaderOutput['taskDetails']>([
      'tasks',
      'details',
      { boardId: data.board.id, taskId: data.taskDetails.id }
    ]);

    return companyDetails && taskDetails
      ? [
          { title: 'Asset Management', link: '/asset-management' },
          { title: companyDetails.name, link: `/asset-management/companies/${companyDetails.id}` },
          { title: taskDetails.external_id }
        ]
      : [{ title: 'Asset Management', link: '/asset-management' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
