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

const REQUIRED_FIELDS: Record<string, string[]> = {
  site_level_details: ['name', 'address', 'city', 'state', 'zip_code', 'system_size_ac', 'system_size_dc'],
  asset_overview: ['module_quantity', 'inverter_quantity', 'project_type'],
  ownership: ['guarantor'],
  tax_equity: [],
  key_dates: ['mechanical_completion_date', 'substantial_completion_date', 'final_completion_date'],
  o_and_m: ['provider', 'agreement_effective_date', 'o_and_m_escalator', 'production_guarantee'],
  interconnection: ['provider', 'ppa_effective_date', 'production_guarantee'],
  epc_contractor: ['provider', 'agreement_effective_date'],
  community_solar_manager: [],
  insurance_provider: [],
  vegetation_vendor: [],
  offtaker: ['offtaker_name'],
  compliance: [],
  site_lease: ['landlord', 'tenant', 'property_size', 'effective_date', 'rent_commencement', 'rent_amount']
};

const checkMissingFields = (data: Record<string, any> | null | undefined, requiredFields: string[]): boolean => {
  if (!data || requiredFields.length === 0) return false;
  return requiredFields.some(field => {
    const value = data[field];
    return value === null || value === undefined || value === '';
  });
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

    const cardDataMap: Record<string, Record<string, any> | null | undefined> = {
      site_level_details: siteData.site_level_details,
      asset_overview: siteData.asset_overview,
      ownership: siteData.ownership,
      tax_equity: siteData.tax_equity,
      key_dates: siteData.key_dates,
      o_and_m: siteData.o_and_m,
      interconnection: siteData.interconnection,
      epc_contractor: siteData.epc_contractor,
      community_solar_manager: siteData.community_solar_manager,
      insurance_provider: siteData.insurance_provider,
      vegetation_vendor: siteData.vegetation_vendor,
      offtaker: siteData.offtaker,
      compliance: siteData.compliance,
      site_lease: siteData.site_lease
    };

    return DEFAULT_CARD_ORDER.map(id => ({
      id,
      title: CARD_TITLES[id] || id,
      content: cardContentMap[id],
      hasMissingFields: checkMissingFields(cardDataMap[id], REQUIRED_FIELDS[id] || [])
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
