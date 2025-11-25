import { FC, useEffect, useRef, useState } from 'react';
import { models, Report } from 'powerbi-client';
import { PowerBIEmbed } from 'powerbi-client-react';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../../api';
import Box from '@mui/material/Box';

interface CompanyType {
  id: string;
  name: string;
}

interface Type {
  id: string;
  name: string;
  web_url: string;
  embed_url: string;
}

interface PowerBIReportProps {
  filters?: {
    company: CompanyType;
    site: CompanyType | null;
    type: Type;
    start_date: string;
    end_date: string;
  };
}
const PowerBIReport: FC<PowerBIReportProps> = ({ filters }) => {
  const reportId = filters?.type?.id;
  const reportRef = useRef<Report | null>(null);
  const [reportConfig, setReportConfig] = useState<models.IReportEmbedConfiguration>({
    type: 'report',
    embedUrl: '',
    accessToken: '',
    id: '',
    tokenType: models.TokenType.Embed,
    settings: {
      panes: {},
      navContentPaneEnabled: false,
      background: models.BackgroundType.Transparent
    }
  });

  const { data: reportsResponseData } = useQuery({
    queryFn: () => ApiClient.reports.getReportToken(reportId ? reportId : ''),
    queryKey: ['reports-token', { reportId }],
    staleTime: 0
  });

  useEffect(() => {
    setReportConfig(prevConfig => ({
      ...prevConfig,
      embedUrl: `${filters?.type?.embed_url}&filter=DimDate/Date%20ge%20${filters?.start_date}%20and%20DimDate/Date%20le%20${filters?.end_date}%20and%20DimSite/SiteId%20eq%20${filters?.site?.id}`,
      accessToken: reportsResponseData?.embed_token,
      id: reportId
    }));
  }, [reportsResponseData, filters, reportId]);

  return (
    <Box marginTop="20px">
      <PowerBIEmbed
        embedConfig={reportConfig}
        cssClassName="power-bi-report-class"
        getEmbeddedComponent={embeddedReport => {
          reportRef.current = embeddedReport as Report;
        }}
      />
    </Box>
  );
};

export default PowerBIReport;
