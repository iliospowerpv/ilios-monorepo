import React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import type { ReconciliationRow } from '../../../../../../../api';

/**
 * Read-only parse-state indicators for a reconciliation row's source document
 * version. These are purely informational signals surfaced from the parse-state
 * read model — they NEVER influence status, blocking level, required action, or
 * any baseline logic. Each chip renders only when its boolean indicator is true.
 */
interface IndicatorDef {
  key: keyof ReconciliationRow;
  label: string;
  description: string;
  color: ChipProps['color'];
}

const INDICATORS: IndicatorDef[] = [
  {
    key: 'source_document_uploaded_not_parsed',
    label: 'Source not parsed',
    description:
      'The source document version was uploaded but has not been parsed yet. Parsing happens in the Data Room.',
    color: 'warning'
  },
  {
    key: 'parse_failed',
    label: 'Source parse failed',
    description: 'The most recent parse attempt on the source document version failed. Retry parsing in the Data Room.',
    color: 'error'
  },
  {
    key: 'parsed_no_usable_fields',
    label: 'No usable fields',
    description: 'The source document version was parsed but produced no fields usable for this screen.',
    color: 'warning'
  },
  {
    key: 'source_document_not_current_version',
    label: 'Not current version',
    description:
      'The source document for this value is not the current version of its document. Review the version in the Data Room.',
    color: 'default'
  },
  {
    key: 'source_document_type_lacks_operational_schema',
    label: 'Generic schema only',
    description:
      'The source document type only has a generic contractual schema, so no operational/equipment fields are extracted from it.',
    color: 'default'
  }
];

export const ParseStateIndicatorChips: React.FC<{ row: ReconciliationRow }> = ({ row }) => {
  const active = INDICATORS.filter(ind => row[ind.key] === true);
  if (active.length === 0) {
    return null;
  }
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.25 }} data-testid="reconciliation-parse-indicators">
      {active.map(ind => (
        <BootstrapTooltip key={ind.key} title={ind.description} placement="top">
          <Chip
            label={ind.label}
            color={ind.color}
            size="small"
            variant="outlined"
            sx={{ height: 18, '& .MuiChip-label': { px: 0.75, fontSize: 10 } }}
            data-testid={`reconciliation-parse-indicator-${ind.key}`}
          />
        </BootstrapTooltip>
      ))}
    </Box>
  );
};

export default ParseStateIndicatorChips;
