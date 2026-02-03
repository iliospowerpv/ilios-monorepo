import { QueryClient } from '@tanstack/react-query';
import { RouteHandle } from '../../../../handles';
import { createLoader } from './loader';
import { BREADCRUMB_LABELS, CANONICAL_ROUTES } from '../../../../utils/breadcrumbs';

type LoaderOutput = Awaited<ReturnType<ReturnType<typeof createLoader>>>;

export const createHandle = (queryClient: QueryClient) => {
  const crumbsBuilder = (data: any) => {
    if (
      typeof data?.siteData?.id !== 'number' ||
      typeof data?.companyData?.id !== 'number' ||
      typeof data?.documentInfo?.id !== 'number'
    ) {
      return [];
    }
    const siteDetails = queryClient.getQueryData<LoaderOutput['siteData']>([
      'site',
      'crumbs',
      'Diligence',
      { siteId: data.siteData.id }
    ]);
    const companyDetails = queryClient.getQueryData<LoaderOutput['companyData']>([
      'company',
      'crumbs',
      'Diligence',
      { companyId: data.companyData.id }
    ]);
    const documentInfo = queryClient.getQueryData<LoaderOutput['documentInfo']>([
      'documents',
      'info',
      { siteId: data.siteData.id, documentId: data.documentInfo.id }
    ]);

    return siteDetails && companyDetails && documentInfo
      ? [
          { title: BREADCRUMB_LABELS.DATA_ROOM, link: '/due-diligence' },
          { title: companyDetails.name, link: `/due-diligence/companies/${companyDetails.id}/sites` },
          { title: siteDetails.name, link: CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB(siteDetails.id, 'data-room') },
          { title: documentInfo.name }
        ]
      : [{ title: BREADCRUMB_LABELS.DATA_ROOM, link: '/due-diligence' }, { title: '...' }];
  };

  const getAIAssistantConfig = (data: any) => {
    const siteId = data?.siteData?.id;

    if (typeof siteId === 'number') {
      return {
        enabled: true,
        siteId
      };
    }

    return {
      enabled: false,
      siteId: -1
    };
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'due-diligence',
    enabledFeatures: { ['ai-assistant']: { generateConfig: getAIAssistantConfig } }
  });
};
