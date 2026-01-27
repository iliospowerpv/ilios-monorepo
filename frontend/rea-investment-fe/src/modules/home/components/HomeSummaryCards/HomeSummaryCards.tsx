import React from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import AssignmentIcon from '@mui/icons-material/Assignment';
import NotificationsIcon from '@mui/icons-material/Notifications';

interface HomeSummaryCardsProps {
  companiesCount: number;
  projectsCount: number;
  pendingTasksCount: number;
  notificationsCount: number;
  isLoading?: boolean;
}

interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, icon, color }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" component="div" sx={{ fontWeight: 600 }}>
            {value}
          </Typography>
        </Box>
        <Box
          sx={{
            backgroundColor: `${color}15`,
            borderRadius: 2,
            p: 1.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {React.cloneElement(icon as React.ReactElement, { sx: { color, fontSize: 32 } })}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

export const HomeSummaryCards: React.FC<HomeSummaryCardsProps> = ({
  companiesCount,
  projectsCount,
  pendingTasksCount,
  notificationsCount,
  isLoading
}) => {
  if (isLoading) {
    return (
      <Grid container spacing={3}>
        {[1, 2, 3, 4].map(i => (
          <Grid item xs={12} sm={6} md={3} key={i}>
            <Card sx={{ height: 100 }}>
              <CardContent>
                <Typography color="text.secondary">Loading...</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  const cards = [
    {
      title: 'Companies',
      value: companiesCount,
      icon: <BusinessIcon />,
      color: '#1976d2'
    },
    {
      title: 'Projects',
      value: projectsCount,
      icon: <FolderIcon />,
      color: '#2e7d32'
    },
    {
      title: 'Pending Tasks',
      value: pendingTasksCount,
      icon: <AssignmentIcon />,
      color: '#ed6c02'
    },
    {
      title: 'Notifications',
      value: notificationsCount,
      icon: <NotificationsIcon />,
      color: '#9c27b0'
    }
  ];

  return (
    <Grid container spacing={3}>
      {cards.map(card => (
        <Grid item xs={12} sm={6} md={3} key={card.title}>
          <SummaryCard {...card} />
        </Grid>
      ))}
    </Grid>
  );
};

export default HomeSummaryCards;
