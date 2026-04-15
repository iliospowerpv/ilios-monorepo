import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Grid from '@mui/material/Grid';
import SearchIcon from '@mui/icons-material/Search';
import BusinessIcon from '@mui/icons-material/Business';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useNavigate } from 'react-router-dom';
import { useEntityContext } from '../../contexts/entityContext';

export const CompaniesPickerView: React.FC = () => {
  const { companies, projects, isLoading } = useAccessibleEntities();
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const { setCurrentCompany, setCurrentScope } = useEntityContext();

  const filteredCompanies = search
    ? companies.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
    : companies;

  const handleCompanyClick = (company: { id: number; name: string }) => {
    setCurrentCompany(company);
    setCurrentScope('company');
    navigate(`/project-hub/companies/${company.id}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Loading companies...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <BusinessIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight={600}>
          Select a Company
        </Typography>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Choose a company to view its details and projects.
      </Typography>

      <TextField
        placeholder="Search companies..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        fullWidth
        sx={{ mb: 4, maxWidth: 400 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          )
        }}
      />

      <Grid container spacing={2}>
        {filteredCompanies.map(company => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={company.id}>
            <Paper
              sx={{
                p: 3,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateY(-2px)',
                  boxShadow: 2
                }
              }}
              onClick={() => handleCompanyClick(company)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <BusinessIcon color="primary" />
                <Box>
                  <Typography variant="subtitle1" fontWeight={500}>
                    {company.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {projects.filter(p => p.company_id === company.id).length} projects
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {filteredCompanies.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <Typography color="text.secondary">
            {search ? 'No companies match your search.' : 'No companies available.'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default CompaniesPickerView;
