import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Companies, { CompaniesRef } from './components/Companies';
import Sites from './components/Sites';
import ActualProduction from '../../../../components/charts/ActualProduction/ActualProduction';
import { ApiClient } from '../../../../api';

export const PortfolioPage: React.FC = () => {
  const [selectedCompany, setSelectedCompany] = React.useState<{ id: number; name: string } | null>(null);
  const [companiesDataRendered, setCompaniesDataRendered] = React.useState<boolean>(false);

  const companiesTableRef = React.useRef<CompaniesRef | null>(null);

  const {
    data: companyPerformanceData,
    isFetching: isFetchingCompanyPerformanceData,
    error: errorLoadingCompanyPerformanceData,
    refetch: refetchCompanyPerformanceData
  } = useQuery({
    queryFn: () => ApiClient.investorDashboard.companyAggregatedPerformance(selectedCompany?.id ?? -1),
    queryKey: ['companies', 'aggregated-performance', { companyId: selectedCompany?.id }],
    enabled: !!selectedCompany
  });

  React.useEffect(() => {
    if (errorLoadingCompanyPerformanceData) {
      companiesTableRef.current?.refetchData();
    }
  }, [errorLoadingCompanyPerformanceData]);

  const onCompaniesDataRendered = React.useCallback(
    () => setTimeout(() => setCompaniesDataRendered(true), 0),
    [setCompaniesDataRendered]
  );

  return (
    <Box maxWidth="1800px" mx="auto" paddingTop="0" paddingBottom="24px" sx={{ flexGrow: 1 }}>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        My Portfolio
      </Typography>
      <Grid container spacing={2} pt="-24px">
        <Grid item xs={12} sm={12} md={6} lg={7}>
          <Box
            sx={{
              mt: '16px',
              borderRight: '1px solid #0000001F',
              borderLeft: '1px solid #0000001F',
              borderTop: '1px solid #0000001F'
            }}
          >
            <Typography variant="h6" fontSize="24px" p="16px">
              Companies
            </Typography>
          </Box>
          <Companies
            ref={companiesTableRef}
            onCompaniesDataRendered={onCompaniesDataRendered}
            onCompanySelected={setSelectedCompany}
          />
        </Grid>
        <Grid item xs={12} sm={12} md={6} lg={5}>
          <Box py="16px" position="relative" display="flex">
            <ActualProduction
              title={selectedCompany?.name ? `${selectedCompany?.name} Production` : 'Actual Production'}
              scope="investor-dashboard"
              data={companyPerformanceData}
              isFetchingCompanyData={isFetchingCompanyPerformanceData}
              errorLoadingCompanyData={errorLoadingCompanyPerformanceData}
              companiesDataRendered={companiesDataRendered}
              onClickRefetch={refetchCompanyPerformanceData}
            />
          </Box>
        </Grid>
        <Grid item xs={12}>
          <Box
            sx={{
              mt: '16px',
              borderRight: '1px solid #0000001F',
              borderLeft: '1px solid #0000001F',
              borderTop: '1px solid #0000001F'
            }}
          >
            <Typography variant="h6" fontSize="24px" p="16px">
              Sites
            </Typography>
          </Box>
          <Sites />
        </Grid>
      </Grid>
    </Box>
  );
};

export default PortfolioPage;
