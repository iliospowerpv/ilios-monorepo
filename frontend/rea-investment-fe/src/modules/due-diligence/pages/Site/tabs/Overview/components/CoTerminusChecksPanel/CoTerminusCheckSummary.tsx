import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';

import { statusIconMapping } from './TermCheckResult';

export interface SummaryItem {
  status: string;
  count: number;
}

interface CoTerminusCheckSummaryProps {
  summaryItems: SummaryItem[];
}

const checkSummaryEntries: Record<string, { title: string; iconNode: React.ReactNode }> = {
  Equal: {
    title: 'Terms Match',
    iconNode: statusIconMapping['Equal']
  },
  'Not Equal': {
    title: `Terms Don't Match`,
    iconNode: statusIconMapping['Not Equal']
  },
  Ambiguous: {
    title: 'Uncertain Results',
    iconNode: statusIconMapping['Ambiguous']
  },
  'N/A': {
    title: 'Data Incomplete',
    iconNode: statusIconMapping['N/A']
  }
};

export const CoTerminusCheckSummary: React.FC<CoTerminusCheckSummaryProps> = ({ summaryItems }) => {
  const countPerStatusCategoryMap = React.useMemo(() => {
    const map = new Map<string, number | undefined>();
    for (const entry of summaryItems) {
      const { status, count } = entry;
      map.set(status, count);
    }
    return map;
  }, [summaryItems]);

  return (
    <Box width="100%" px="16px" pt="16px" pb="4px" mb="16px" bgcolor="#0000000A">
      <Typography variant="h6" mb="8px">
        Summary
      </Typography>
      <Box width="100%">
        {Object.keys(checkSummaryEntries).map(summaryKey => (
          <Stack
            key={summaryKey}
            alignItems="center"
            direction="row"
            flexWrap="nowrap"
            gap={1}
            py="8px"
            sx={{ '&:not(:last-child)': { borderBottom: '1px solid #E0E0E0' } }}
            data-testid={`co-terminus-summary-${summaryKey}-entry`}
          >
            <Stack direction="row" gap={1} alignItems="center" flexWrap="nowrap" width="60%">
              {checkSummaryEntries[summaryKey].iconNode}
              <Typography variant="body2">{checkSummaryEntries[summaryKey].title}</Typography>
            </Stack>
            <Typography width="40%" textAlign="right" sx={{ wordBreak: 'break-all' }}>
              {countPerStatusCategoryMap.get(summaryKey) ?? 0}
            </Typography>
          </Stack>
        ))}
      </Box>
    </Box>
  );
};

export default CoTerminusCheckSummary;
