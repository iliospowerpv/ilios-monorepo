import { RouteHandle } from '../../../../handles';

export const createHandle = () => {
  const crumbsBuilder = (data: any) => {
    if (typeof data?.data?.id !== 'number') {
      return [];
    }

    return data?.data?.id && data?.siteData?.name
      ? [
          { title: 'Diligence', link: '/due-diligence' },
          { title: data?.data?.name, link: `/due-diligence/companies/${data?.data?.id}/sites` },
          { title: data?.siteData?.name }
        ]
      : [{ title: 'Diligence', link: '/due-diligence' }, { title: '...' }];
  };

  const getAIAssistantConfig = (data: any) => {
    const siteId = data?.siteData?.id;

    if (typeof siteId !== 'number') {
      return {
        enabled: false,
        siteId: -1
      };
    }

    return {
      enabled: true,
      siteId
    };
  };

  return RouteHandle.createHandle({
    crumbsBuilder: crumbsBuilder,
    moduleId: 'due-diligence',
    enabledFeatures: { ['ai-assistant']: { generateConfig: getAIAssistantConfig } }
  });
};
