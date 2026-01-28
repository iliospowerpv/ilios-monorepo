import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Skeleton from '@mui/material/Skeleton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';

import { ApiClient } from '../../../../api';
import { AddCompanyDialog, AddUserDialog } from '../../components/dialogs';

export const PortfolioLevelPage: React.FC = () => {
  const navigate = useNavigate();
  const [isAddCompanyOpen, setIsAddCompanyOpen] = useState(false);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);

  const { data: workspace, isLoading } = useQuery({
    queryKey: ['workspace'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    staleTime: 5 * 60 * 1000
  });

  const companies = workspace?.companies || [];
  const summary = workspace?.summary;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Portfolio Admin
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Manage all companies, projects, and users across the portfolio
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<PersonAddIcon />}
            onClick={() => setIsAddUserOpen(true)}
          >
            Add User
          </Button>
          <Button
            variant="contained"
            startIcon={<AddBusinessIcon />}
            onClick={() => setIsAddCompanyOpen(true)}
          >
            Add Company
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <BusinessIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.companies_count || 0}
                  </Typography>
                  <Typography color="text.secondary">Companies</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FolderIcon sx={{ fontSize: 40, color: 'success.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.projects_count || 0}
                  </Typography>
                  <Typography color="text.secondary">Projects</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <PersonAddIcon sx={{ fontSize: 40, color: 'warning.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.pending_tasks_count || 0}
                  </Typography>
                  <Typography color="text.secondary">Pending Tasks</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Companies
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Company Name</TableCell>
                  <TableCell align="center">Projects</TableCell>
                  <TableCell>Access Source</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  [1, 2, 3].map(i => (
                    <TableRow key={i}>
                      <TableCell><Skeleton /></TableCell>
                      <TableCell><Skeleton /></TableCell>
                      <TableCell><Skeleton width={80} /></TableCell>
                      <TableCell><Skeleton width={40} /></TableCell>
                    </TableRow>
                  ))
                ) : companies.length > 0 ? (
                  companies.map(company => (
                    <TableRow
                      key={company.company_id}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/portfolio-admin/companies/${company.company_id}`)}
                    >
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <BusinessIcon fontSize="small" color="action" />
                          {company.company_name}
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          size="small"
                          label={`${company.project_count} project${company.project_count !== 1 ? 's' : ''}`}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={company.access_source}
                          color={company.access_source === 'membership' ? 'primary' : 'default'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton size="small">
                          <ChevronRightIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography color="text.secondary" sx={{ py: 3 }}>
                        No companies found. Add your first company to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <AddCompanyDialog
        open={isAddCompanyOpen}
        onClose={() => setIsAddCompanyOpen(false)}
      />

      <AddUserDialog
        open={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        level="portfolio"
      />
    </Box>
  );
};

export default PortfolioLevelPage;
