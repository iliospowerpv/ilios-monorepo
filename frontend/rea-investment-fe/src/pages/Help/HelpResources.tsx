import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import RocketLaunchOutlinedIcon from '@mui/icons-material/RocketLaunchOutlined';
import AccountBalanceOutlinedIcon from '@mui/icons-material/AccountBalanceOutlined';
import TimelineOutlinedIcon from '@mui/icons-material/TimelineOutlined';
import HelpOutlineOutlinedIcon from '@mui/icons-material/HelpOutlineOutlined';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import Snackbar from '@mui/material/Snackbar';

interface HelpSection {
  title: string;
  icon: React.ReactNode;
  items: { title: string; id: string }[];
}

const helpSections: HelpSection[] = [
  {
    title: 'Getting Started',
    icon: <RocketLaunchOutlinedIcon color="primary" />,
    items: [
      { title: 'Understanding Projects vs Deals', id: 'projects-vs-deals' },
      { title: 'Navigating Portfolio, Companies, and Projects', id: 'navigation-guide' }
    ]
  },
  {
    title: 'Finance & Diligence',
    icon: <AccountBalanceOutlinedIcon color="primary" />,
    items: [
      { title: 'How finance readiness works', id: 'finance-readiness' },
      { title: 'Deal to Project conversion explained', id: 'deal-conversion' }
    ]
  },
  {
    title: 'Operations & Lifecycle',
    icon: <TimelineOutlinedIcon color="primary" />,
    items: [
      { title: 'Lifecycle stages explained', id: 'lifecycle-stages' },
      { title: 'When modules become active', id: 'module-activation' }
    ]
  },
  {
    title: 'FAQs',
    icon: <HelpOutlineOutlinedIcon color="primary" />,
    items: []
  }
];

const HelpResources: React.FC = () => {
  const navigate = useNavigate();
  const [snackbarOpen, setSnackbarOpen] = React.useState(false);

  const handleItemClick = () => {
    setSnackbarOpen(true);
  };

  return (
    <Box sx={{ p: 4, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Help & Resources
        </Typography>
      </Stack>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Guides, FAQs, and walkthroughs for using the Ilios platform.
      </Typography>

      <Grid container spacing={3}>
        {helpSections.map(section => (
          <Grid item xs={12} md={6} key={section.title}>
            <Paper elevation={0} sx={{ border: 1, borderColor: 'divider', height: '100%' }}>
              <Box
                sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}
              >
                {section.icon}
                <Typography variant="h6" fontWeight={600}>
                  {section.title}
                </Typography>
              </Box>
              <List disablePadding>
                {section.items.length > 0 ? (
                  section.items.map((item, index) => (
                    <ListItem key={item.id} disablePadding divider={index < section.items.length - 1}>
                      <ListItemButton onClick={handleItemClick}>
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          <ArticleOutlinedIcon fontSize="small" color="action" />
                        </ListItemIcon>
                        <ListItemText primary={item.title} />
                        <ChevronRightIcon color="action" />
                      </ListItemButton>
                    </ListItem>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText
                      primary="Content coming soon"
                      primaryTypographyProps={{ color: 'text.secondary', fontStyle: 'italic' }}
                    />
                  </ListItem>
                )}
              </List>
            </Paper>
          </Grid>
        ))}
      </Grid>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Documentation coming soon."
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default HelpResources;
