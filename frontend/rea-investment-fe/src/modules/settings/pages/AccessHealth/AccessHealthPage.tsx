import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  Alert,
  AlertTitle,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stack,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import RefreshIcon from '@mui/icons-material/Refresh';
import BuildIcon from '@mui/icons-material/Build';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';

import { ApiClient, type ValidationResult, type ValidationIssue, type RepairResult } from '../../../../api';

const AccessHealthPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin', 'access-health'],
    queryFn: () => ApiClient.admin.getAccessHealth()
  });

  const repairOrphanedMutation = useMutation({
    mutationFn: () => ApiClient.admin.repairOrphanedMemberships(),
    onSuccess: (result: RepairResult) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'access-health'] });
      alert(`${result.message}`);
    },
    onError: (err: Error) => {
      alert(`Repair failed: ${err.message}`);
    }
  });

  const repairInv1Mutation = useMutation({
    mutationFn: () => ApiClient.admin.repairInv1Violations(),
    onSuccess: (result: RepairResult) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'access-health'] });
      alert(`${result.message}`);
    },
    onError: (err: Error) => {
      alert(`Repair failed: ${err.message}`);
    }
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Running health checks...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <AlertTitle>Error</AlertTitle>
        Failed to load access health data. You may not have permission to view this page.
      </Alert>
    );
  }

  const getStatusColor = (passed: boolean): 'success' | 'error' => (passed ? 'success' : 'error');
  const getStatusIcon = (passed: boolean) => (passed ? <CheckCircleIcon /> : <ErrorIcon />);

  const renderIssuesTable = (issues: ValidationIssue[]) => {
    if (issues.length === 0) return null;

    return (
      <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Table</TableCell>
              <TableCell>Record ID</TableCell>
              <TableCell>Details</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {issues.slice(0, 50).map((issue, idx) => (
              <TableRow key={idx}>
                <TableCell>
                  <Chip label={issue.issue_type} size="small" color="warning" />
                </TableCell>
                <TableCell>{issue.table}</TableCell>
                <TableCell>{issue.record_id}</TableCell>
                <TableCell sx={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {issue.details}
                </TableCell>
              </TableRow>
            ))}
            {issues.length > 50 && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography variant="body2" color="text.secondary">
                    ...and {issues.length - 50} more issues
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  const renderValidationCard = (validation: ValidationResult) => {
    const hasRepairAction =
      (validation.check_name === 'INV-1 Integrity' && !validation.passed) ||
      (validation.check_name === 'Orphaned Memberships' && !validation.passed);

    return (
      <Accordion key={validation.check_name} defaultExpanded={!validation.passed}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
            {getStatusIcon(validation.passed)}
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="subtitle1" fontWeight="medium">
                {validation.check_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {validation.description}
              </Typography>
            </Box>
            <Chip
              label={validation.passed ? 'Passed' : `${validation.issue_count} Issues`}
              color={getStatusColor(validation.passed)}
              size="small"
            />
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          {validation.passed ? (
            <Alert severity="success" icon={<CheckCircleIcon />}>
              No issues found for this check.
            </Alert>
          ) : (
            <Box>
              <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
                Found {validation.issue_count} issue(s) that may need attention.
              </Alert>

              {hasRepairAction && (
                <Box sx={{ mb: 2 }}>
                  {validation.check_name === 'INV-1 Integrity' && (
                    <Button
                      variant="contained"
                      color="warning"
                      startIcon={<BuildIcon />}
                      onClick={() => repairInv1Mutation.mutate()}
                      disabled={repairInv1Mutation.isPending}
                    >
                      {repairInv1Mutation.isPending ? 'Repairing...' : 'Repair INV-1 Violations'}
                    </Button>
                  )}
                  {validation.check_name === 'Orphaned Memberships' && (
                    <Button
                      variant="contained"
                      color="warning"
                      startIcon={<BuildIcon />}
                      onClick={() => repairOrphanedMutation.mutate()}
                      disabled={repairOrphanedMutation.isPending}
                    >
                      {repairOrphanedMutation.isPending ? 'Repairing...' : 'Remove Orphaned Records'}
                    </Button>
                  )}
                </Box>
              )}

              {renderIssuesTable(validation.issues)}
            </Box>
          )}
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Card sx={{ mb: 3 }}>
        <CardHeader
          avatar={<HealthAndSafetyIcon color="primary" fontSize="large" />}
          title={
            <Typography variant="h5" fontWeight="medium">
              Access Model Health
            </Typography>
          }
          subheader="System-wide validation checks for access model data integrity"
          action={
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => refetch()}>
              Refresh
            </Button>
          }
        />
        <Divider />
        <CardContent>
          <Stack direction="row" spacing={3} alignItems="center">
            <Box>
              <Typography variant="h3" color={data?.overall_healthy ? 'success.main' : 'warning.main'}>
                {data?.overall_healthy ? (
                  <CheckCircleIcon sx={{ fontSize: 48 }} />
                ) : (
                  <WarningIcon sx={{ fontSize: 48 }} />
                )}
              </Typography>
            </Box>
            <Box>
              <Typography variant="h6">{data?.overall_healthy ? 'All Checks Passed' : 'Issues Detected'}</Typography>
              <Typography variant="body2" color="text.secondary">
                {data?.total_issues === 0
                  ? 'No data integrity issues found.'
                  : `${data?.total_issues} total issue(s) across ${data?.validations.filter(v => !v.passed).length} check(s).`}
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1 }} />
            <Stack direction="row" spacing={1}>
              <Chip
                icon={<CheckCircleIcon />}
                label={`${data?.validations.filter(v => v.passed).length} Passed`}
                color="success"
                variant="outlined"
              />
              <Chip
                icon={<ErrorIcon />}
                label={`${data?.validations.filter(v => !v.passed).length} Failed`}
                color={data?.validations.some(v => !v.passed) ? 'error' : 'default'}
                variant="outlined"
              />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6" sx={{ mb: 2 }}>
        Validation Checks
      </Typography>

      {data?.validations.map(renderValidationCard)}
    </Box>
  );
};

export default AccessHealthPage;
