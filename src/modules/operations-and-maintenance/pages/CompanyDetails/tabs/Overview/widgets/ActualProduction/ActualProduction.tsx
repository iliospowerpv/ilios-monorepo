import React from 'react';
import { useQuery } from '@tanstack/react-query';

import ActualProduction from '../../../../../../../../components/charts/ActualProduction/ActualProduction';
import { ApiClient } from '../../../../../../../../api';

interface ActualProductionProps {
  companyId: number;
}

export const ActualProductionWrapper: React.FC<ActualProductionProps> = ({ companyId }) => {
  const {
    data: companyData,
    isFetching: isFetchingCompanyData,
    error: errorLoadingCompanyData,
    refetch: refetchCompanyData
  } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.getCompanyDashboardProduction(companyId),
    queryKey: ['companies', 'actual-production-chart', { companyId }],
    refetchInterval: 15 * 60 * 1000
  });

  return (
    <ActualProduction
      title="Production"
      data={companyData}
      scope="O&M"
      isFetchingCompanyData={isFetchingCompanyData}
      errorLoadingCompanyData={errorLoadingCompanyData}
      onClickRefetch={refetchCompanyData}
    />
  );
};

export default ActualProductionWrapper;
