import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createLoader } from './loader';

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

    const companyInfo = siteDetails?.company;

    return siteDetails && companyInfo && taskDetails
      ? [
          { title: 'Asset Management', link: '/asset-management' },
          { title: companyInfo.name, link: `/asset-management/companies/${companyInfo.id}` },
          { title: siteDetails.name, link: `/asset-management/companies/${companyInfo.id}/sites/${siteDetails.id}` },
          { title: taskDetails.external_id }
        ]
      : [{ title: 'Asset Management', link: '/asset-management' }, { title: '...' }];
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'asset-management'
  });
};
