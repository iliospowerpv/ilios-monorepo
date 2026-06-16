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
import { ExecutiveSummary } from './components/ExecutiveSummary';
import { UnderwritingReadiness } from './components/UnderwritingReadiness';
import formatFloatValue from '../../../../../../utils/formatters/formatFloatValue';
import { OverviewProvenanceProvider } from './components/provenance/ReconciliationProvenanceContext';

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
  site_level_details: ['name', 'address', 'city', 'state', 'system_size_ac', 'system_size_dc'],
  asset_overview: ['module_quantity', 'inverter_quantity', 'project_type'],
  ownership: ['guarantor', 'ownership_structure'],
  tax_equity: ['tax_equity_provider'],
  key_dates: ['placed_in_service_date', 'permission_to_operate'],
  o_and_m: ['provider', 'agreement_effective_date', 'production_guarantee'],
  interconnection: ['provider', 'ppa_effective_date'],
  epc_contractor: ['provider', 'agreement_effective_date'],
  community_solar_manager: [],
  insurance_provider: ['insurance_provider'],
  vegetation_vendor: [],
  offtaker: ['offtaker_name'],
  compliance: [],
  site_lease: ['landlord', 'effective_date']
};

const CRITICAL_CARDS = ['site_level_details', 'ownership', 'key_dates', 'interconnection', 'insurance_provider'];

interface MissingFieldInfo {
  cardId: string;
  cardTitle: string;
  fieldName: string;
  fieldLabel: string;
}

const getMissingFields = (data: Record<string, any> | null | undefined, requiredFields: string[]): string[] => {
  if (!data || requiredFields.length === 0) return [];
  return requiredFields.filter(field => {
    const value = data[field];
    return value === null || value === undefined || value === '';
  });
};

const generateHeaderSummary = (cardId: string, data: Record<string, any> | null | undefined): string => {
  if (!data) return '';

  switch (cardId) {
    case 'site_level_details': {
      const parts = [];
      if (data.system_size_dc) parts.push(`${formatFloatValue(data.system_size_dc)} kW DC`);
      if (data.status) parts.push(data.status);
      if (data.city && data.state) parts.push(`${data.city}, ${data.state}`);
      return parts.join(' | ');
    }
    case 'asset_overview': {
      const parts = [];
      if (data.module_quantity) parts.push(`${data.module_quantity} modules`);
      if (data.inverter_quantity) parts.push(`${data.inverter_quantity} inverters`);
      if (data.project_type) parts.push(data.project_type);
      return parts.join(' | ');
    }
    case 'ownership': {
      const parts = [];
      if (data.guarantor) parts.push(`Guarantor: ${data.guarantor}`);
      if (data.ownership_structure) parts.push(data.ownership_structure);
      return parts.join(' | ');
    }
    case 'tax_equity': {
      const parts = [];
      if (data.tax_equity_provider) parts.push(data.tax_equity_provider);
      if (data.tax_equity_fund) parts.push(data.tax_equity_fund);
      return parts.join(' | ');
    }
    case 'key_dates': {
      const parts = [];
      if (data.permission_to_operate) parts.push(`PTO: ${data.permission_to_operate}`);
      if (data.placed_in_service_date) parts.push(`COD: ${data.placed_in_service_date}`);
      return parts.join(' | ');
    }
    case 'o_and_m': {
      const parts = [];
      if (data.provider) parts.push(data.provider);
      if (data.production_guarantee) parts.push(`${data.production_guarantee}% guarantee`);
      return parts.join(' | ');
    }
    case 'interconnection': {
      const parts = [];
      if (data.provider) parts.push(data.provider);
      if (data.ppa_term) parts.push(`${data.ppa_term} yr term`);
      return parts.join(' | ');
    }
    case 'epc_contractor': {
      return data.provider || '';
    }
    case 'insurance_provider': {
      return data.insurance_provider || '';
    }
    case 'offtaker': {
      return data.offtaker_name || '';
    }
    case 'site_lease': {
      const parts = [];
      if (data.landlord) parts.push(`Landlord: ${data.landlord}`);
      if (data.rent_amount) parts.push(`$${data.rent_amount}/mo`);
      return parts.join(' | ');
    }
    default:
      return '';
  }
};

const DEFAULT_CARD_ORDER = [
  'site_level_details',
  'key_dates',
  'ownership',
  'asset_overview',
  'interconnection',
  'tax_equity',
  'o_and_m',
  'epc_contractor',
  'insurance_provider',
  'offtaker',
  'site_lease',
  'community_solar_manager',
  'vegetation_vendor',
  'compliance'
];

export const OverviewTab: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { id: siteId } = siteDetails;
  const portfolioId = siteDetails.company?.id;

  const { data: siteData, isLoading: isLoadingSiteData } = useQuery({
    queryFn: () => ApiClient.assetManagement.siteInfo(siteId),
    queryKey: ['sites', 'info', siteId],
    throwOnError: true
  });

  const { cardItems, allMissingFields, criticalCompleteCount } = React.useMemo(() => {
    if (!siteData) return { cardItems: [], allMissingFields: [], criticalCompleteCount: 0 };

    const cardContentMap: Record<string, React.ReactNode> = {
      site_level_details: <SiteLevelDetailsCard siteId={siteId} data={siteData.site_level_details} hideHeader />,
      asset_overview: <AssetOverviewCard siteId={siteId} data={siteData.asset_overview} hideHeader />,
      ownership: <OwnershipCard siteId={siteId} data={siteData.ownership} hideHeader portfolioId={portfolioId} />,
      tax_equity: <TaxEquityCard siteId={siteId} data={siteData.tax_equity} hideHeader portfolioId={portfolioId} />,
      key_dates: <KeyDatesCard siteId={siteId} data={siteData.key_dates} hideHeader />,
      o_and_m: <OMCard siteId={siteId} data={siteData.o_and_m} hideHeader portfolioId={portfolioId} />,
      interconnection: (
        <InterconnectionUtilityProviderCard
          siteId={siteId}
          data={siteData.interconnection}
          hideHeader
          portfolioId={portfolioId}
        />
      ),
      epc_contractor: (
        <EPCContractorCard siteId={siteId} data={siteData.epc_contractor} hideHeader portfolioId={portfolioId} />
      ),
      community_solar_manager: (
        <CommunitySolarManagerCard
          siteId={siteId}
          data={siteData.community_solar_manager}
          hideHeader
          portfolioId={portfolioId}
        />
      ),
      insurance_provider: (
        <InsuranceProviderCard
          siteId={siteId}
          data={siteData.insurance_provider}
          hideHeader
          portfolioId={portfolioId}
        />
      ),
      vegetation_vendor: (
        <VegetationVendorCard siteId={siteId} data={siteData.vegetation_vendor} hideHeader portfolioId={portfolioId} />
      ),
      offtaker: <OfftakerCard siteId={siteId} data={siteData.offtaker} hideHeader portfolioId={portfolioId} />,
      compliance: <ComplianceCard siteId={siteId} data={siteData.compliance} hideHeader portfolioId={portfolioId} />,
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

    const missingFieldsCollector: MissingFieldInfo[] = [];
    let criticalComplete = 0;

    const items: CardItem[] = DEFAULT_CARD_ORDER.map(id => {
      const requiredFields = REQUIRED_FIELDS[id] || [];
      const missingFields = getMissingFields(cardDataMap[id], requiredFields);
      const isCritical = CRITICAL_CARDS.includes(id);

      if (isCritical && missingFields.length === 0) {
        criticalComplete++;
      }

      missingFields.forEach(fieldName => {
        if (isCritical) {
          missingFieldsCollector.push({
            cardId: id,
            cardTitle: CARD_TITLES[id] || id,
            fieldName,
            fieldLabel: fieldName
          });
        }
      });

      return {
        id,
        title: CARD_TITLES[id] || id,
        content: cardContentMap[id],
        hasMissingFields: missingFields.length > 0,
        missingFieldCount: missingFields.length,
        missingFieldNames: missingFields,
        headerSummary: generateHeaderSummary(id, cardDataMap[id])
      };
    });

    return {
      cardItems: items,
      allMissingFields: missingFieldsCollector,
      criticalCompleteCount: criticalComplete
    };
  }, [siteId, siteData]);

  if (isLoadingSiteData || !siteData) return null;

  return (
    <Box>
      <ExecutiveSummary
        siteLevelDetails={siteData.site_level_details}
        keyDates={siteData.key_dates}
        interconnection={siteData.interconnection}
      />
      <UnderwritingReadiness
        missingFields={allMissingFields}
        totalCriticalCards={CRITICAL_CARDS.length}
        completeCards={criticalCompleteCount}
      />
      <OverviewProvenanceProvider siteId={siteId}>
        <DraggableCardLayout cards={cardItems} storageKey={`overview_cards_${siteId}`} columns={3} />
      </OverviewProvenanceProvider>
    </Box>
  );
};

export default OverviewTab;
