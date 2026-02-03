import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  InputAdornment,
  Chip,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  IconButton,
  Menu,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import ClearIcon from '@mui/icons-material/Clear';
import { useNavigate } from 'react-router-dom';
import {
  Deal,
  SalesStage,
  SALES_STAGE_LABELS,
  SALES_STAGE_COLORS,
  ACTIVE_PIPELINE_STAGES,
  CLOSED_STAGES
} from '../../types';

interface DealsListViewProps {
  deals: Deal[];
}

type SortField =
  | 'name'
  | 'sales_stage'
  | 'developer_name'
  | 'pipeline_value'
  | 'system_size_ac'
  | 'next_action_date'
  | 'updated_at';
type SortDirection = 'asc' | 'desc';

const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

const getStageOrder = (stage: SalesStage): number => {
  const allStages = [...ACTIVE_PIPELINE_STAGES, ...CLOSED_STAGES];
  return allStages.indexOf(stage);
};

interface DealRowProps {
  deal: Deal;
  onView: () => void;
  onEdit: () => void;
}

const DealRow: React.FC<DealRowProps> = ({ deal, onView, onEdit }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleView = () => {
    handleMenuClose();
    onView();
  };

  const handleEdit = () => {
    handleMenuClose();
    onEdit();
  };

  const isOverdue = deal.next_action_date && new Date(deal.next_action_date) < new Date();

  return (
    <TableRow hover sx={{ opacity: deal.is_converted ? 0.6 : 1, cursor: 'pointer' }} onClick={onView}>
      <TableCell>
        <Box>
          <Typography variant="body2" fontWeight={500}>
            {deal.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {deal.company_name || `Company ${deal.company_id}`}
          </Typography>
        </Box>
      </TableCell>
      <TableCell>
        <Chip
          label={SALES_STAGE_LABELS[deal.sales_stage]}
          size="small"
          sx={{
            bgcolor: SALES_STAGE_COLORS[deal.sales_stage],
            fontSize: '0.7rem',
            height: 22
          }}
        />
        {deal.is_converted && (
          <Chip label="Converted" size="small" color="success" sx={{ ml: 0.5, fontSize: '0.65rem', height: 20 }} />
        )}
      </TableCell>
      <TableCell>{deal.developer_name || '-'}</TableCell>
      <TableCell align="right">{formatCurrency(deal.pipeline_value)}</TableCell>
      <TableCell align="right">{deal.system_size_ac ? `${deal.system_size_ac} MW` : '-'}</TableCell>
      <TableCell>
        {deal.next_action_date ? (
          <Chip
            label={formatDate(deal.next_action_date)}
            size="small"
            color={isOverdue ? 'error' : 'default'}
            variant="outlined"
            sx={{ fontSize: '0.7rem', height: 22 }}
          />
        ) : (
          '-'
        )}
      </TableCell>
      <TableCell>{formatDate(deal.updated_at)}</TableCell>
      <TableCell align="right" onClick={e => e.stopPropagation()}>
        <IconButton size="small" onClick={handleMenuClick}>
          <MoreVertIcon fontSize="small" />
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          open={menuOpen}
          onClose={handleMenuClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <MenuItem onClick={handleView}>
            <ListItemIcon>
              <VisibilityIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>View</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleEdit} disabled={deal.is_converted}>
            <ListItemIcon>
              <EditIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Edit</ListItemText>
          </MenuItem>
        </Menu>
      </TableCell>
    </TableRow>
  );
};

export const DealsListView: React.FC<DealsListViewProps> = ({ deals }) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<SalesStage | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showFilters, setShowFilters] = useState(false);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedDeals = useMemo(() => {
    let result = [...deals];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        deal =>
          deal.name.toLowerCase().includes(query) ||
          (deal.developer_name && deal.developer_name.toLowerCase().includes(query)) ||
          (deal.company_name && deal.company_name.toLowerCase().includes(query)) ||
          (deal.city && deal.city.toLowerCase().includes(query)) ||
          (deal.state && deal.state.toLowerCase().includes(query))
      );
    }

    if (stageFilter !== 'all') {
      result = result.filter(deal => deal.sales_stage === stageFilter);
    }

    result.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'sales_stage':
          comparison = getStageOrder(a.sales_stage) - getStageOrder(b.sales_stage);
          break;
        case 'developer_name':
          comparison = (a.developer_name || '').localeCompare(b.developer_name || '');
          break;
        case 'pipeline_value':
          comparison = (a.pipeline_value || 0) - (b.pipeline_value || 0);
          break;
        case 'system_size_ac':
          comparison = (a.system_size_ac || 0) - (b.system_size_ac || 0);
          break;
        case 'next_action_date': {
          const dateA = a.next_action_date ? new Date(a.next_action_date).getTime() : 0;
          const dateB = b.next_action_date ? new Date(b.next_action_date).getTime() : 0;
          comparison = dateA - dateB;
          break;
        }
        case 'updated_at':
          comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [deals, searchQuery, stageFilter, sortField, sortDirection]);

  const handleDealView = (dealId: number) => {
    navigate(`/acquisitions/deal/${dealId}`);
  };

  const handleDealEdit = (dealId: number) => {
    navigate(`/acquisitions/deal/${dealId}?mode=edit`);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setStageFilter('all');
  };

  const hasActiveFilters = searchQuery || stageFilter !== 'all';

  const allStages = [...ACTIVE_PIPELINE_STAGES, ...CLOSED_STAGES];

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" gap={1}>
          <TextField
            size="small"
            placeholder="Search deals..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            sx={{ minWidth: 250 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              )
            }}
          />

          <IconButton onClick={() => setShowFilters(!showFilters)} color={showFilters ? 'primary' : 'default'}>
            <FilterListIcon />
          </IconButton>

          {showFilters && (
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Stage</InputLabel>
              <Select<SalesStage | 'all'>
                value={stageFilter}
                label="Stage"
                onChange={e => setStageFilter(e.target.value as SalesStage | 'all')}
              >
                <MenuItem value="all">All Stages</MenuItem>
                {allStages.map(stage => (
                  <MenuItem key={stage} value={stage}>
                    {SALES_STAGE_LABELS[stage]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {hasActiveFilters && (
            <Chip label="Clear filters" size="small" onDelete={clearFilters} onClick={clearFilters} />
          )}

          <Box sx={{ flex: 1 }} />

          <Typography variant="body2" color="text.secondary">
            {filteredAndSortedDeals.length} deal{filteredAndSortedDeals.length !== 1 ? 's' : ''}
          </Typography>
        </Stack>
      </Paper>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>
                <TableSortLabel
                  active={sortField === 'name'}
                  direction={sortField === 'name' ? sortDirection : 'asc'}
                  onClick={() => handleSort('name')}
                >
                  Deal Name
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <TableSortLabel
                  active={sortField === 'sales_stage'}
                  direction={sortField === 'sales_stage' ? sortDirection : 'asc'}
                  onClick={() => handleSort('sales_stage')}
                >
                  Stage
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <TableSortLabel
                  active={sortField === 'developer_name'}
                  direction={sortField === 'developer_name' ? sortDirection : 'asc'}
                  onClick={() => handleSort('developer_name')}
                >
                  Developer
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }} align="right">
                <TableSortLabel
                  active={sortField === 'pipeline_value'}
                  direction={sortField === 'pipeline_value' ? sortDirection : 'asc'}
                  onClick={() => handleSort('pipeline_value')}
                >
                  Pipeline Value
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }} align="right">
                <TableSortLabel
                  active={sortField === 'system_size_ac'}
                  direction={sortField === 'system_size_ac' ? sortDirection : 'asc'}
                  onClick={() => handleSort('system_size_ac')}
                >
                  Size (AC)
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <TableSortLabel
                  active={sortField === 'next_action_date'}
                  direction={sortField === 'next_action_date' ? sortDirection : 'asc'}
                  onClick={() => handleSort('next_action_date')}
                >
                  Next Action
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <TableSortLabel
                  active={sortField === 'updated_at'}
                  direction={sortField === 'updated_at' ? sortDirection : 'asc'}
                  onClick={() => handleSort('updated_at')}
                >
                  Last Updated
                </TableSortLabel>
              </TableCell>
              <TableCell align="right" sx={{ width: 50 }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredAndSortedDeals.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    {hasActiveFilters ? 'No deals match your search criteria' : 'No deals found'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredAndSortedDeals.map(deal => (
                <DealRow
                  key={deal.id}
                  deal={deal}
                  onView={() => handleDealView(deal.id)}
                  onEdit={() => handleDealEdit(deal.id)}
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DealsListView;
