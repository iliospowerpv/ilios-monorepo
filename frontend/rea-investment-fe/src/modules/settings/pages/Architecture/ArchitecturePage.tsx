import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  CardHeader,
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
  TextField,
  Link as MuiLink,
  List,
  ListItemButton,
  ListItemText,
  Divider,
  Button
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import StorageIcon from '@mui/icons-material/Storage';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import ApiIcon from '@mui/icons-material/Api';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

import { ApiClient } from '../../../../api';

const API_BASE = process.env.REACT_APP_URL || '';

const apiLinks = [
  { label: 'Swagger UI (interactive)', href: `${API_BASE}/docs` },
  { label: 'ReDoc (reference)', href: `${API_BASE}/redoc` },
  { label: 'OpenAPI schema (JSON)', href: `${API_BASE}/openapi.json` }
];

const ApiGuideSection: React.FC = () => (
  <Card sx={{ mb: 3 }}>
    <CardHeader
      avatar={<ApiIcon color="primary" />}
      title={<Typography variant="h6">API Reference</Typography>}
      subheader="Live, auto-generated documentation for the backend HTTP API."
    />
    <Divider />
    <CardContent>
      <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
        {apiLinks.map(link => (
          <Button
            key={link.href}
            component={MuiLink}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            variant="outlined"
            size="small"
            endIcon={<OpenInNewIcon />}
          >
            {link.label}
          </Button>
        ))}
      </Stack>
    </CardContent>
  </Card>
);

const DatabaseSection: React.FC = () => {
  const [filter, setFilter] = React.useState('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['settings', 'architecture', 'database'],
    queryFn: () => ApiClient.systemSettings.getDatabaseStructure()
  });

  const tables = React.useMemo(() => {
    const all = data?.tables ?? [];
    const term = filter.trim().toLowerCase();
    if (!term) return all;
    return all.filter(t => t.name.toLowerCase().includes(term));
  }, [data, filter]);

  return (
    <Card sx={{ mb: 3 }}>
      <CardHeader
        avatar={<StorageIcon color="primary" />}
        title={<Typography variant="h6">Database Structure</Typography>}
        subheader={
          data
            ? `Schema "${data.schema_name}" — ${data.table_count} tables (live introspection).`
            : 'Live introspection of the application schema.'
        }
      />
      <Divider />
      <CardContent>
        {isLoading && (
          <Box display="flex" alignItems="center" gap={2} py={2}>
            <CircularProgress size={20} />
            <Typography variant="body2">Loading schema...</Typography>
          </Box>
        )}
        {error && (
          <Alert severity="error">
            <AlertTitle>Error</AlertTitle>
            Failed to load database structure.
          </Alert>
        )}
        {data && (
          <>
            <TextField
              size="small"
              fullWidth
              placeholder="Filter tables by name..."
              value={filter}
              onChange={e => setFilter(e.target.value)}
              sx={{ mb: 2 }}
            />
            {tables.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No tables match &quot;{filter}&quot;.
              </Typography>
            ) : (
              tables.map(table => (
                <Accordion key={table.name} disableGutters>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ width: '100%' }}>
                      <Typography variant="subtitle2" sx={{ fontFamily: 'monospace', flexGrow: 1 }}>
                        {table.name}
                      </Typography>
                      <Chip size="small" variant="outlined" label={`${table.column_count} cols`} />
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Column</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Nullable</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {table.columns.map(col => (
                            <TableRow key={col.name}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{col.name}</TableCell>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{col.data_type}</TableCell>
                              <TableCell>{col.is_nullable ? 'YES' : 'NO'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </AccordionDetails>
                </Accordion>
              ))
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const DocsSection: React.FC = () => {
  const [selectedKey, setSelectedKey] = React.useState<string | null>(null);

  const {
    data: list,
    isLoading: listLoading,
    error: listError
  } = useQuery({
    queryKey: ['settings', 'architecture', 'docs'],
    queryFn: () => ApiClient.systemSettings.listArchitectureDocs()
  });

  const documents = React.useMemo(() => list?.documents ?? [], [list]);

  React.useEffect(() => {
    if (!selectedKey && documents.length > 0) {
      setSelectedKey(documents[0].key);
    }
  }, [documents, selectedKey]);

  const {
    data: doc,
    isLoading: docLoading,
    error: docError
  } = useQuery({
    queryKey: ['settings', 'architecture', 'doc', selectedKey],
    queryFn: () => ApiClient.systemSettings.getArchitectureDoc(selectedKey as string),
    enabled: Boolean(selectedKey)
  });

  return (
    <Card>
      <CardHeader
        avatar={<MenuBookIcon color="primary" />}
        title={<Typography variant="h6">Architecture &amp; Operational Notes</Typography>}
        subheader="Curated reference documents maintained alongside the codebase."
      />
      <Divider />
      <CardContent>
        {listLoading && (
          <Box display="flex" alignItems="center" gap={2} py={2}>
            <CircularProgress size={20} />
            <Typography variant="body2">Loading documents...</Typography>
          </Box>
        )}
        {listError && (
          <Alert severity="error">
            <AlertTitle>Error</AlertTitle>
            Failed to load document list.
          </Alert>
        )}
        {list && documents.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No reference documents are available.
          </Typography>
        )}
        {documents.length > 0 && (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <Paper variant="outlined" sx={{ width: { xs: '100%', md: 280 }, flexShrink: 0 }}>
              <List dense disablePadding>
                {documents.map(d => (
                  <ListItemButton key={d.key} selected={d.key === selectedKey} onClick={() => setSelectedKey(d.key)}>
                    <ListItemText
                      primary={d.title}
                      secondary={`${d.path} · ${formatBytes(d.size_bytes)}`}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: 'medium' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItemButton>
                ))}
              </List>
            </Paper>
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              {docLoading && (
                <Box display="flex" alignItems="center" gap={2} py={2}>
                  <CircularProgress size={20} />
                  <Typography variant="body2">Loading document...</Typography>
                </Box>
              )}
              {docError && (
                <Alert severity="error">
                  <AlertTitle>Error</AlertTitle>
                  Failed to load document.
                </Alert>
              )}
              {doc && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  {doc.truncated && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                      This document is large and has been truncated for display.
                    </Alert>
                  )}
                  <Typography
                    component="pre"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontFamily: 'monospace',
                      fontSize: 13,
                      m: 0,
                      maxHeight: 600,
                      overflow: 'auto'
                    }}
                  >
                    {doc.content}
                  </Typography>
                </Paper>
              )}
            </Box>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

const ArchitecturePage: React.FC = () => (
  <Box sx={{ p: 3 }}>
    <ApiGuideSection />
    <DatabaseSection />
    <DocsSection />
  </Box>
);

export default ArchitecturePage;
