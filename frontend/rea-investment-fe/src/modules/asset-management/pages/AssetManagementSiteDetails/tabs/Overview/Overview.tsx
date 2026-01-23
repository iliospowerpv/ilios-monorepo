import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';

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
import { DraggableCardLayout, CardItem } from './components/DraggableLayout';

const CARD_TITLES: Record<string, string> = {
  site_level_details: 'Site Level Details',
  asset_overview: 'Asset Overview',
  ownership: 'Ownership',
  tax_equity: 'Tax Equity',
  key_dates: 'Key Dates',
  o_and_m: 'O&M',
  interconnection: 'Interconnection',
  epc_contractor: 'EPC Contractor',
  community_solar_manager: 'Community Solar Manager',
  insurance_provider: 'Insurance Provider',
  vegetation_vendor: 'Vegetation Vendor',
  offtaker: 'Offtaker',
  compliance: 'Compliance',
  site_lease: 'Site Lease'
};

const DEFAULT_CARD_ORDER = [
  'site_level_details',
  'asset_overview',
  'ownership',
  'epc_contractor',
  'tax_equity',
  'key_dates',
  'vegetation_vendor',
  'o_and_m',
  'interconnection',
  'site_lease',
  'community_solar_manager',
  'insurance_provider',
  'compliance',
  'offtaker'
];

export const OverviewTab: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { id: siteId } = siteDetails;

  const { data: siteData, isLoading: isLoadingSiteData } = useQuery({
    queryFn: () => ApiClient.assetManagement.siteInfo(siteId),
    queryKey: ['sites', 'info', siteId],
    throwOnError: true
  });

  const cardItems: CardItem[] = React.useMemo(() => {
    if (!siteData) return [];

    const cardContentMap: Record<string, React.ReactNode> = {
      site_level_details: <SiteLevelDetailsCard siteId={siteId} data={siteData.site_level_details} hideHeader />,
      asset_overview: <AssetOverviewCard siteId={siteId} data={siteData.asset_overview} hideHeader />,
      ownership: <OwnershipCard siteId={siteId} data={siteData.ownership} hideHeader />,
      tax_equity: <TaxEquityCard siteId={siteId} data={siteData.tax_equity} hideHeader />,
      key_dates: <KeyDatesCard siteId={siteId} data={siteData.key_dates} hideHeader />,
      o_and_m: <OMCard siteId={siteId} data={siteData.o_and_m} hideHeader />,
      interconnection: (
        <InterconnectionUtilityProviderCard siteId={siteId} data={siteData.interconnection} hideHeader />
      ),
      epc_contractor: <EPCContractorCard siteId={siteId} data={siteData.epc_contractor} hideHeader />,
      community_solar_manager: (
        <CommunitySolarManagerCard siteId={siteId} data={siteData.community_solar_manager} hideHeader />
      ),
      insurance_provider: <InsuranceProviderCard siteId={siteId} data={siteData.insurance_provider} hideHeader />,
      vegetation_vendor: <VegetationVendorCard siteId={siteId} data={siteData.vegetation_vendor} hideHeader />,
      offtaker: <OfftakerCard siteId={siteId} data={siteData.offtaker} hideHeader />,
      compliance: <ComplianceCard siteId={siteId} data={siteData.compliance} hideHeader />,
      site_lease: <SiteLeaseCard siteId={siteId} data={siteData.site_lease} hideHeader />
    };

    return DEFAULT_CARD_ORDER.map(id => ({
      id,
      title: CARD_TITLES[id] || id,
      content: cardContentMap[id]
    }));
  }, [siteId, siteData]);

  if (isLoadingSiteData || !siteData) return null;

  return (
    <Box>
      <DraggableCardLayout cards={cardItems} storageKey={`overview_cards_${siteId}`} columns={3} />
    </Box>
  );
};

export default OverviewTab;
