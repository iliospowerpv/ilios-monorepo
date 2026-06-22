import React from 'react';
import dayjs from 'dayjs';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import CircularProgress from '@mui/material/CircularProgress';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ReplayIcon from '@mui/icons-material/Replay';
import PushPinOutlinedIcon from '@mui/icons-material/PushPinOutlined';
import { ParseStateSummary, ParseState, ParseNextAction, NoUsableFieldsReason } from '../../../../../api';

type ChipColor = 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';

interface ParseStateDisplay {
  label: string;
  color: ChipColor;
  description: string;
}

// Honest, plain-language copy for each lifecycle state. No state is implied as
// "done" unless it genuinely is; empty/failed states are explicit, never silent.
const getParseStateDisplay = (summary: ParseStateSummary): ParseStateDisplay => {
  const state: ParseState = summary.parse_state;
  const reason: NoUsableFieldsReason | null = summary.no_usable_fields_reason;
  const isEquipment = summary.selected_document_type.is_equipment_type;
  const isGenericStub = summary.selected_document_type.is_generic_contractual_stub;

  switch (state) {
    case 'not_yet_parsed':
      return {
        label: 'Not parsed yet',
        color: 'default',
        description: 'This document version has not been parsed. Run the parser to extract its fields.'
      };
    case 'parsing_in_progress':
      return {
        label: 'Parsing in progress',
        color: 'info',
        description: 'A parse run is currently queued or processing. This can take a few minutes.'
      };
    case 'parse_failed':
      return {
        label: 'Parse failed',
        color: 'error',
        description: 'The most recent parse attempt did not complete. You can retry parsing this document.'
      };
    case 'parsed_no_usable_fields': {
      if (reason === 'generic_contractual_schema' && isEquipment) {
        return {
          label: 'Parsed — no equipment fields',
          color: 'warning',
          description:
            'This equipment datasheet was parsed with the generic contractual schema, which cannot capture ' +
            'equipment specifications. A specialized equipment extraction schema is required (planned for a later phase).'
        };
      }
      if (reason === 'generic_contractual_schema') {
        return {
          label: 'Parsed — no specialized fields',
          color: 'warning',
          description:
            'This document was parsed with the generic contractual schema and no specialized fields matched. ' +
            'If this is not a generic contract, consider changing the document type.'
        };
      }
      if (reason === 'no_schema_fields') {
        return {
          label: 'Parsed — no schema',
          color: 'warning',
          description: 'No extraction schema is configured for this document type, so nothing could be captured.'
        };
      }
      if (reason === 'fields_did_not_map') {
        return {
          label: 'Parsed — fields did not map',
          color: 'warning',
          description:
            'The parser returned values, but none matched this document type’s schema. ' +
            'Consider changing the document type.'
        };
      }
      // no_fields_found (or unspecified)
      return {
        label: 'Parsed — no fields found',
        color: 'warning',
        description: 'Parsing completed but no extractable fields were found in this document.'
      };
    }
    case 'parsed_awaiting_review':
      return {
        label: 'Parsed — awaiting review',
        color: 'info',
        description: `${summary.reviewable_field_count} extracted field${
          summary.reviewable_field_count === 1 ? '' : 's'
        } ready to review and accept.`
      };
    case 'accepted_or_overridden':
      return {
        label: 'Accepted / overridden',
        color: 'primary',
        description: `${summary.accepted_overridden_count} value${
          summary.accepted_overridden_count === 1 ? '' : 's'
        } accepted or overridden. Review or promote to current assumptions.`
      };
    case 'promoted':
      return {
        label: 'Promoted',
        color: 'success',
        description: `${summary.promoted_count} value${
          summary.promoted_count === 1 ? '' : 's'
        } promoted into current assumptions.`
      };
    default:
      return {
        label: String(state),
        color: 'default',
        description: ''
      };
  }
};

const WARNING_COPY: Record<string, string> = {
  sole_non_current_version:
    'This is the only version of this document and it is not marked as the current version. ' +
    'Mark it current so its values are used downstream.',
  not_current_version: 'This version is not the current version of its document.',
  no_equipment_extraction_schema:
    'No specialized equipment extraction schema exists for this document type yet (planned for a later phase).',
  generic_contractual_schema: 'This document type currently uses the shared generic contractual schema.',
  parse_failed: 'The most recent parse attempt failed.'
};

interface ParseStatusCardProps {
  summary: ParseStateSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  onParse: () => void;
  onRetry: () => void;
  onSetCurrent?: () => void;
  isParsing?: boolean;
  isSettingCurrent?: boolean;
  canSetCurrent?: boolean;
}

const formatTimestamp = (value: string | null | undefined): string =>
  value ? dayjs(value).format('MMM D, YYYY h:mm A') : 'Unavailable';

const ParseStatusCard: React.FC<ParseStatusCardProps> = ({
  summary,
  isLoading,
  isError,
  onParse,
  onRetry,
  onSetCurrent,
  isParsing = false,
  isSettingCurrent = false,
  canSetCurrent = false
}) => {
  if (isLoading) {
    return (
      <Box sx={{ p: 2, mb: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
        <Skeleton variant="text" width="40%" />
        <Skeleton variant="text" width="70%" />
        <Skeleton variant="text" width="55%" />
      </Box>
    );
  }

  if (isError || !summary) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Parse status is unavailable for this document version right now.
      </Alert>
    );
  }

  const display = getParseStateDisplay(summary);
  const { selected_document_type: docType, file_version: version, latest_run: latestRun } = summary;
  const nextAction: ParseNextAction = summary.next_action;

  const showParseButton = nextAction === 'parse_document';
  const showRetryButton = nextAction === 'retry_parse';
  const showSetCurrentButton =
    canSetCurrent &&
    !!onSetCurrent &&
    (summary.warnings.includes('sole_non_current_version') || summary.warnings.includes('not_current_version'));

  return (
    <Box
      data-testid="parse-status-card"
      sx={{ p: 2, mb: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Parse Status
          </Typography>
          <Chip size="small" color={display.color} label={display.label} sx={{ fontWeight: 500, fontSize: '12px' }} />
          {summary.active_reprocess_in_progress && (
            <Chip
              size="small"
              color="info"
              variant="outlined"
              icon={<CircularProgress size={12} color="inherit" />}
              label="Reprocessing"
              sx={{ fontSize: '11px' }}
            />
          )}
        </Box>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {display.description}
      </Typography>

      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 0.5, mb: 1.5 }}>
        <Chip
          size="small"
          variant="outlined"
          label={`Type: ${docType.display || docType.key || 'Unspecified'}`}
          sx={{ fontSize: '11px' }}
        />
        {docType.is_equipment_type && (
          <Chip size="small" color="secondary" variant="outlined" label="Equipment" sx={{ fontSize: '11px' }} />
        )}
        {docType.is_generic_contractual_stub && (
          <Chip size="small" color="warning" variant="outlined" label="Generic schema" sx={{ fontSize: '11px' }} />
        )}
        <Chip
          size="small"
          variant="outlined"
          color={version.is_current_version ? 'success' : 'default'}
          label={version.is_current_version ? `${version.version_display} · Current` : `${version.version_display} · Not current`}
          sx={{ fontSize: '11px' }}
        />
      </Stack>

      <Divider sx={{ my: 1 }} />

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 1 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            Reviewable
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {summary.reviewable_field_count}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            Accepted / overridden
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {summary.accepted_overridden_count}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            Promoted
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {summary.promoted_count}
          </Typography>
        </Box>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        Last parse attempt: {formatTimestamp(summary.last_parse_attempt_at)}
      </Typography>
      {latestRun && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          Latest run #{latestRun.extraction_run_number ?? latestRun.id} · {latestRun.status}
        </Typography>
      )}

      {summary.warnings.length > 0 && (
        <Stack spacing={1} sx={{ mt: 1.5 }}>
          {summary.warnings.map(code => (
            <Alert key={code} severity="warning" sx={{ py: 0, fontSize: '13px' }}>
              {WARNING_COPY[code] || code}
            </Alert>
          ))}
        </Stack>
      )}

      {(showParseButton || showRetryButton || showSetCurrentButton) && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
          {showParseButton && (
            <Button
              variant="contained"
              size="small"
              onClick={onParse}
              disabled={isParsing}
              startIcon={isParsing ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
            >
              Parse with AI
            </Button>
          )}
          {showRetryButton && (
            <Button
              variant="outlined"
              color="error"
              size="small"
              onClick={onRetry}
              disabled={isParsing}
              startIcon={isParsing ? <CircularProgress size={16} color="inherit" /> : <ReplayIcon />}
            >
              Retry parse
            </Button>
          )}
          {showSetCurrentButton && (
            <Button
              variant="outlined"
              size="small"
              onClick={onSetCurrent}
              disabled={isSettingCurrent}
              startIcon={isSettingCurrent ? <CircularProgress size={16} color="inherit" /> : <PushPinOutlinedIcon />}
            >
              Set as current version
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
};

export default ParseStatusCard;
