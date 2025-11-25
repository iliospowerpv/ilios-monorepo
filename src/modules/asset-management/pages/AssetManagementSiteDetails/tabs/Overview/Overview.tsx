import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';

import { ApiClient } from '../../../../../../api';

import { AssetManagementSiteDetailsTabProps } from '../types';

import { EPCContractorCard } from './components/information-cards/EPCContractor/EPCContractor';
import { SiteLeaseCard } from './components/information-cards/SiteLease/SiteLease';
import { VegetationVendorCard } from './components/information-cards/VegetationVendor/VegetationVendor';
import { OMCard } from './components/information-cards/OM/OM';
import { InsuranceProviderCard } from './components/information-cards/InsuranceProvider/InsuranceProvider';
import { AssetOverviewCard } from './components/information-cards/AssetOverview/AssetOverview';
import { TaxEquityCard } from './components/information-cards/TaxEquity/TaxEquity';
import { OfftakerCard } from './components/information-cards/Offtaker/Offtaker';
import { KeyDatesCard } from './components/information-cards/KeyDates/KeyDates';
import { ComplianceCard } from './components/information-cards/Compliance/Compliance';
import { OwnershipCard } from './components/information-cards/Ownership/Ownership';
import { CommunitySolarManagerCard } from './components/information-cards/CommunitySolarManager/CommunitySolarManager';
import { InterconnectionUtilityProviderCard } from './components/information-cards/InterconnectionUtilityProvider/InterconnectionUtilityProvider';
import { SiteLevelDetailsCard } from './components/information-cards/SiteLevelDetails/SiteLevelDetails';

type DetailedSiteInto = Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>;
type InfoCardKeys = keyof DetailedSiteInto;

export const OverviewTab: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { id: siteId } = siteDetails;

  const theme = useTheme();
  const mediumSizeView = useMediaQuery(theme.breakpoints.up('md'));
  const largeSizeView = useMediaQuery(theme.breakpoints.up('lg'));

  const { data: siteData, isLoading: isLoadingSiteData } = useQuery({
    queryFn: () => ApiClient.assetManagement.siteInfo(siteId),
    queryKey: ['sites', 'info', siteId],
    throwOnError: true
  });

  const InfoCardMap: { [key in InfoCardKeys]: React.ReactElement } | null = React.useMemo(
    () =>
      siteData
        ? {
            asset_overview: <AssetOverviewCard siteId={siteId} data={siteData.asset_overview} />,
            ownership: <OwnershipCard siteId={siteId} data={siteData.ownership} />,
            tax_equity: <TaxEquityCard siteId={siteId} data={siteData.tax_equity} />,
            key_dates: <KeyDatesCard siteId={siteId} data={siteData.key_dates} />,
            o_and_m: <OMCard siteId={siteId} data={siteData.o_and_m} />,
            interconnection: <InterconnectionUtilityProviderCard siteId={siteId} data={siteData.interconnection} />,
            epc_contractor: <EPCContractorCard siteId={siteId} data={siteData.epc_contractor} />,
            community_solar_manager: (
              <CommunitySolarManagerCard siteId={siteId} data={siteData.community_solar_manager} />
            ),
            insurance_provider: <InsuranceProviderCard siteId={siteId} data={siteData.insurance_provider} />,
            vegetation_vendor: <VegetationVendorCard siteId={siteId} data={siteData.vegetation_vendor} />,
            offtaker: <OfftakerCard siteId={siteId} data={siteData.offtaker} />,
            compliance: <ComplianceCard siteId={siteId} data={siteData.compliance} />,
            site_lease: <SiteLeaseCard siteId={siteId} data={siteData.site_lease} />,
            site_level_details: <SiteLevelDetailsCard siteId={siteId} data={siteData.site_level_details} />
          }
        : null,
    [siteId, siteData]
  );

  if (isLoadingSiteData || !siteData || !InfoCardMap) return null;

  if (largeSizeView) {
    return (
      <Grid mb="12px" container spacing={1}>
        <Grid item xs={4}>
          <Stack direction="column" spacing={1}>
            {InfoCardMap['site_level_details']}
            {InfoCardMap['epc_contractor']}
            {InfoCardMap['vegetation_vendor']}
            {InfoCardMap['site_lease']}
          </Stack>
        </Grid>
        <Grid item xs={4}>
          <Stack direction="column" spacing={1}>
            {InfoCardMap['asset_overview']}
            {InfoCardMap['tax_equity']}
            {InfoCardMap['o_and_m']}
            {InfoCardMap['community_solar_manager']}
            {InfoCardMap['compliance']}
          </Stack>
        </Grid>
        <Grid item xs={4}>
          <Stack direction="column" spacing={1}>
            {InfoCardMap['ownership']}
            {InfoCardMap['key_dates']}
            {InfoCardMap['interconnection']}
            {InfoCardMap['insurance_provider']}
            {InfoCardMap['offtaker']}
          </Stack>
        </Grid>
      </Grid>
    );
  }

  if (mediumSizeView) {
    return (
      <Grid mb="12px" container spacing={1}>
        <Grid item xs={6}>
          <Stack direction="column" spacing={1}>
            {InfoCardMap['site_level_details']}
            {InfoCardMap['o_and_m']}
            {InfoCardMap['epc_contractor']}
            {InfoCardMap['community_solar_manager']}
            {InfoCardMap['offtaker']}
            {InfoCardMap['site_lease']}
          </Stack>
        </Grid>
        <Grid item xs={6}>
          <Stack direction="column" spacing={1}>
            {InfoCardMap['asset_overview']}
            {InfoCardMap['ownership']}
            {InfoCardMap['tax_equity']}
            {InfoCardMap['key_dates']}
            {InfoCardMap['interconnection']}
            {InfoCardMap['insurance_provider']}
            {InfoCardMap['vegetation_vendor']}
            {InfoCardMap['compliance']}
          </Stack>
        </Grid>
      </Grid>
    );
  }

  return (
    <Stack mb="12px" direction="column" spacing={1}>
      {InfoCardMap['site_level_details']}
      {InfoCardMap['asset_overview']}
      {InfoCardMap['ownership']}
      {InfoCardMap['tax_equity']}
      {InfoCardMap['key_dates']}
      {InfoCardMap['o_and_m']}
      {InfoCardMap['interconnection']}
      {InfoCardMap['epc_contractor']}
      {InfoCardMap['community_solar_manager']}
      {InfoCardMap['insurance_provider']}
      {InfoCardMap['vegetation_vendor']}
      {InfoCardMap['offtaker']}
      {InfoCardMap['compliance']}
      {InfoCardMap['site_lease']}
    </Stack>
  );
};

export default OverviewTab;
