import React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import type { ReconciliationRow } from '../../../../../../../api';
import StatusChip from './StatusChip';
import WarningChips from './WarningChips';
import { CATEGORY_ORDER, categoryLabel, formatValue, formatConfidence, PLACEHOLDER } from '../utils';

interface ReconciliationTableProps {
  rows: ReconciliationRow[];
  helpTargets: Record<string, string>;
}

interface ValueColumn {
  key: keyof ReconciliationRow;
  label: string;
  helpKey: string;
  fallbackHelp: string;
}

const VALUE_COLUMNS: ValueColumn[] = [
  {
    key: 'ai_extracted_value',
    label: 'AI value',
    helpKey: 'ai_extracted_value',
    fallbackHelp: 'What the AI model first read from the source document.'
  },
  {
    key: 'accepted_value',
    label: 'Accepted',
    helpKey: 'accepted_value',
    fallbackHelp: 'The value a reviewer accepted or overrode at the document.'
  },
  {
    key: 'active_fact_value',
    label: 'Active fact',
    helpKey: 'active_fact_value',
    fallbackHelp: 'The current promoted assumption (active project fact).'
  },
  {
    key: 'draft_baseline_value',
    label: 'Draft baseline',
    helpKey: 'draft_baseline_value',
    fallbackHelp: 'Value on the latest draft baseline (not yet active).'
  },
  {
    key: 'active_baseline_value',
    label: 'Active baseline',
    helpKey: 'active_baseline_value',
    fallbackHelp: 'Value on the active baseline driving expected output.'
  },
  {
    key: 'legacy_value',
    label: 'Legacy',
    helpKey: 'legacy_value',
    fallbackHelp: 'Legacy site field — shown for comparison only, never used to build a V2 baseline.'
  }
];

const HeaderCell: React.FC<{ label: string; help?: string }> = ({ label, help }) =>
  help ? (
    <TableCell sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
      <BootstrapTooltip title={help} placement="top">
        <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
          {label}
          <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
        </Box>
      </BootstrapTooltip>
    </TableCell>
  ) : (
    <TableCell sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{label}</TableCell>
  );

const SourceCell: React.FC<{ row: ReconciliationRow }> = ({ row }) => {
  const hasProvenance =
    row.source_document_type || row.evidence_page !== null || row.confidence !== null || row.evidence_snippet;

  if (!hasProvenance) {
    return (
      <Typography variant="body2" color="text.disabled">
        {PLACEHOLDER}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 160 }}>
      <Box>
        <Typography variant="body2">{row.source_document_type || PLACEHOLDER}</Typography>
        <Typography variant="caption" color="text.secondary">
          {row.evidence_page !== null ? `Page ${row.evidence_page}` : 'Page —'}
          {' · '}
          {`Confidence ${formatConfidence(row.confidence)}`}
        </Typography>
      </Box>
      {row.evidence_snippet && (
        <BootstrapTooltip title={row.evidence_snippet} placement="top">
          <InfoOutlinedIcon
            sx={{ fontSize: 16, color: 'text.disabled', cursor: 'help' }}
            data-testid="evidence-snippet-icon"
          />
        </BootstrapTooltip>
      )}
    </Box>
  );
};

const CategorySection: React.FC<{
  category: string;
  rows: ReconciliationRow[];
  helpTargets: Record<string, string>;
}> = ({ category, rows, helpTargets }) => (
  <Paper variant="outlined" sx={{ mb: 3, overflow: 'hidden' }} data-testid={`reconciliation-category-${category}`}>
    <Box sx={{ px: 2, py: 1.5, backgroundColor: 'action.hover' }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        {categoryLabel(category)}{' '}
        <Typography component="span" variant="caption" color="text.secondary">
          ({rows.length})
        </Typography>
      </Typography>
    </Box>
    <TableContainer>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <HeaderCell label="Field" />
            <HeaderCell label="Status" help={helpTargets.status} />
            {VALUE_COLUMNS.map(col => (
              <HeaderCell key={String(col.key)} label={col.label} help={helpTargets[col.helpKey] || col.fallbackHelp} />
            ))}
            <HeaderCell label="Source" help="Document type, page, AI confidence, and evidence snippet (read-only)." />
            <HeaderCell label="Warnings" help={helpTargets.warnings} />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => (
            <TableRow key={row.canonical_field} hover data-testid="reconciliation-row">
              <TableCell sx={{ minWidth: 180 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {row.display_label}
                  </Typography>
                  {row.required_for_baseline && (
                    <BootstrapTooltip title="Required for the weather-adjusted baseline." placement="top">
                      <StarBorderIcon sx={{ fontSize: 14, color: 'warning.main' }} data-testid="required-marker" />
                    </BootstrapTooltip>
                  )}
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {row.canonical_field}
                  {row.candidate_count > 0 ? ` · ${row.candidate_count} candidate(s)` : ''}
                </Typography>
              </TableCell>
              <TableCell>
                <StatusChip status={row.status} />
              </TableCell>
              {VALUE_COLUMNS.map(col => (
                <TableCell key={String(col.key)} sx={{ whiteSpace: 'nowrap' }}>
                  {formatValue(row[col.key] as never)}
                </TableCell>
              ))}
              <TableCell>
                <SourceCell row={row} />
              </TableCell>
              <TableCell sx={{ minWidth: 160 }}>
                <WarningChips warnings={row.warnings} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Paper>
);

export const ReconciliationTable: React.FC<ReconciliationTableProps> = ({ rows, helpTargets }) => {
  const grouped = React.useMemo(() => {
    const map = new Map<string, ReconciliationRow[]>();
    for (const row of rows) {
      const list = map.get(row.category) || [];
      list.push(row);
      map.set(row.category, list);
    }
    const knownOrdered = CATEGORY_ORDER.filter(cat => map.has(cat));
    const extras = Array.from(map.keys()).filter(cat => !CATEGORY_ORDER.includes(cat));
    return [...knownOrdered, ...extras].map(cat => ({ category: cat, rows: map.get(cat) as ReconciliationRow[] }));
  }, [rows]);

  return (
    <Box data-testid="reconciliation-table">
      {grouped.map(group => (
        <CategorySection key={group.category} category={group.category} rows={group.rows} helpTargets={helpTargets} />
      ))}
    </Box>
  );
};

export default ReconciliationTable;
