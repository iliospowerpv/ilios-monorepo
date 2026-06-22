import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import Chip from '@mui/material/Chip';
import MuiLink from '@mui/material/Link';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PublishIcon from '@mui/icons-material/Publish';
import AddTaskIcon from '@mui/icons-material/AddTask';
import { Link as RouterLink } from 'react-router-dom';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import type { ReconciliationRow } from '../../../../../../../api';
import { PromoteVersionDialog } from '../../../../../../../components/promotion';
import StatusChip from './StatusChip';
import WarningChips from './WarningChips';
import ParseStateIndicatorChips from './ParseStateIndicatorChips';
import CreateActionTaskDialog from './CreateActionTaskDialog';
import {
  CATEGORY_ORDER,
  categoryLabel,
  formatValue,
  formatConfidence,
  blockingMeta,
  missingDependencyLabel,
  canPromoteRow,
  canCreateTaskRow,
  ACTIONS_IN_DATA_ROOM,
  PLACEHOLDER
} from '../utils';

interface ReconciliationTableProps {
  rows: ReconciliationRow[];
  helpTargets: Record<string, string>;
  /** Owning site id; used to build the read-only Data Room deep link. */
  siteId?: number | null;
  /** Project name, threaded into the Create Task description. */
  siteName?: string | null;
  /**
   * Whether the viewer holds Diligence edit rights. Gates the in-place Promote
   * and Create Task actions; when false the table is purely read-only.
   */
  canEdit?: boolean;
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

const StatusCell: React.FC<{
  row: ReconciliationRow;
  dataRoomPath: string | null;
  canAct: boolean;
  onPromote: (row: ReconciliationRow) => void;
  onCreateTask: (row: ReconciliationRow) => void;
}> = ({ row, dataRoomPath, canAct, onPromote, onCreateTask }) => {
  const blocking = row.blocking_level ? blockingMeta(row.blocking_level) : null;
  const showDataRoomLink =
    Boolean(row.required_action) && dataRoomPath !== null && ACTIONS_IN_DATA_ROOM.has(row.status);
  const showPromote = canAct && canPromoteRow(row);
  const showCreateTask = canAct && canCreateTaskRow(row);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, minWidth: 200 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
        <StatusChip status={row.status} label={row.status_label} description={row.status_explanation} />
        {blocking && (
          <BootstrapTooltip title={blocking.description} placement="top">
            <Chip
              label={blocking.label}
              color={blocking.color}
              size="small"
              variant="filled"
              data-testid="reconciliation-blocking-chip"
            />
          </BootstrapTooltip>
        )}
      </Box>

      {(showPromote || showCreateTask) && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {showPromote && (
            <BootstrapTooltip
              title="Promote this document version's accepted values into the project's current assumptions."
              placement="top"
            >
              <Button
                size="small"
                variant="outlined"
                startIcon={<PublishIcon sx={{ fontSize: 14 }} />}
                onClick={() => onPromote(row)}
                data-testid="reconciliation-promote-btn"
                sx={{ py: 0.25 }}
              >
                Promote
              </Button>
            </BootstrapTooltip>
          )}
          {showCreateTask && (
            <BootstrapTooltip title="Create a Diligence follow-up task for this field's next step." placement="top">
              <Button
                size="small"
                variant="text"
                startIcon={<AddTaskIcon sx={{ fontSize: 14 }} />}
                onClick={() => onCreateTask(row)}
                data-testid="reconciliation-create-task-btn"
                sx={{ py: 0.25 }}
              >
                Create task
              </Button>
            </BootstrapTooltip>
          )}
        </Box>
      )}

      {row.required_action && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
          <Typography variant="caption" color="text.secondary" data-testid="reconciliation-required-action">
            <Box component="strong" sx={{ color: 'text.primary' }}>
              Next:
            </Box>{' '}
            {row.required_action}
          </Typography>
          {showDataRoomLink && (
            <MuiLink
              component={RouterLink}
              to={dataRoomPath as string}
              variant="caption"
              sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25, alignSelf: 'flex-start' }}
              data-testid="reconciliation-dataroom-link"
            >
              <OpenInNewIcon sx={{ fontSize: 12 }} />
              Open Data Room
            </MuiLink>
          )}
        </Box>
      )}

      {row.missing_dependencies.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.25 }} data-testid="reconciliation-missing-deps">
          {row.missing_dependencies.map(dep => (
            <BootstrapTooltip key={dep} title={`Pending stage: ${missingDependencyLabel(dep)}`} placement="top">
              <Chip
                label={missingDependencyLabel(dep)}
                size="small"
                variant="outlined"
                sx={{ height: 18, '& .MuiChip-label': { px: 0.75, fontSize: 10 } }}
              />
            </BootstrapTooltip>
          ))}
        </Box>
      )}

      <ParseStateIndicatorChips row={row} />
    </Box>
  );
};

const CategorySection: React.FC<{
  category: string;
  rows: ReconciliationRow[];
  helpTargets: Record<string, string>;
  dataRoomPath: string | null;
  canAct: boolean;
  onPromote: (row: ReconciliationRow) => void;
  onCreateTask: (row: ReconciliationRow) => void;
}> = ({ category, rows, helpTargets, dataRoomPath, canAct, onPromote, onCreateTask }) => (
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
                {row.aliases_matched.length > 0 && (
                  <BootstrapTooltip title={`Matched source names: ${row.aliases_matched.join(', ')}`} placement="top">
                    <Typography
                      variant="caption"
                      color="text.disabled"
                      sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25, cursor: 'help' }}
                      data-testid="reconciliation-aliases"
                    >
                      <InfoOutlinedIcon sx={{ fontSize: 12 }} />
                      {row.aliases_matched.length} matched name{row.aliases_matched.length > 1 ? 's' : ''}
                    </Typography>
                  </BootstrapTooltip>
                )}
              </TableCell>
              <TableCell>
                <StatusCell
                  row={row}
                  dataRoomPath={dataRoomPath}
                  canAct={canAct}
                  onPromote={onPromote}
                  onCreateTask={onCreateTask}
                />
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

export const ReconciliationTable: React.FC<ReconciliationTableProps> = ({
  rows,
  helpTargets,
  siteId,
  siteName,
  canEdit
}) => {
  const validSiteId = Number.isSafeInteger(siteId) && (siteId as number) > 0 ? (siteId as number) : null;
  const dataRoomPath = validSiteId !== null ? `/project-hub/projects/${validSiteId}/data-room` : null;
  // Actions need both edit rights and a real site id to target.
  const canAct = Boolean(canEdit) && validSiteId !== null;

  const [promoteRow, setPromoteRow] = React.useState<ReconciliationRow | null>(null);
  const [taskRow, setTaskRow] = React.useState<ReconciliationRow | null>(null);

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
        <CategorySection
          key={group.category}
          category={group.category}
          rows={group.rows}
          helpTargets={helpTargets}
          dataRoomPath={dataRoomPath}
          canAct={canAct}
          onPromote={setPromoteRow}
          onCreateTask={setTaskRow}
        />
      ))}

      {validSiteId !== null && promoteRow && (
        <PromoteVersionDialog
          open
          siteId={validSiteId}
          context={{
            documentId: promoteRow.document_id as number,
            fileId: promoteRow.document_version_id as number,
            launchedFieldLabel: promoteRow.display_label,
            documentTypeLabel: promoteRow.source_document_type
          }}
          onClose={() => setPromoteRow(null)}
        />
      )}

      {validSiteId !== null && taskRow && (
        <CreateActionTaskDialog
          open
          siteId={validSiteId}
          row={taskRow}
          siteName={siteName ?? undefined}
          onClose={() => setTaskRow(null)}
        />
      )}
    </Box>
  );
};

export default ReconciliationTable;
