import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import HomeIcon from '@mui/icons-material/Home';
import FolderIcon from '@mui/icons-material/Folder';
import SettingsIcon from '@mui/icons-material/Settings';
import CelebrationIcon from '@mui/icons-material/Celebration';

interface CompletionScreenProps {
  companyId: number;
  companyName: string;
  projectId: number;
  projectName: string;
  invitedCount: number;
  onStartNew: () => void;
}

export const CompletionScreen: React.FC<CompletionScreenProps> = ({
  companyId,
  companyName,
  projectId,
  projectName,
  invitedCount,
  onStartNew
}) => {
  const navigate = useNavigate();

  const checklist = [
    { label: 'Company configured', value: companyName, complete: true },
    { label: 'Project created/selected', value: projectName, complete: true },
    {
      label: 'Users invited',
      value: invitedCount > 0 ? `${invitedCount} user(s)` : 'Skipped',
      complete: invitedCount > 0
    }
  ];

  return (
    <Box sx={{ textAlign: 'center' }}>
      <Box sx={{ mb: 4 }}>
        <CelebrationIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Setup Complete!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Your project is ready. Here&apos;s what was configured:
        </Typography>
      </Box>

      <Card variant="outlined" sx={{ mb: 4, maxWidth: 400, mx: 'auto' }}>
        <CardContent>
          <List disablePadding>
            {checklist.map((item, index) => (
              <React.Fragment key={item.label}>
                {index > 0 && <Divider />}
                <ListItem>
                  <ListItemIcon>
                    {item.complete ? <CheckCircleIcon color="success" /> : <RadioButtonUncheckedIcon color="action" />}
                  </ListItemIcon>
                  <ListItemText primary={item.label} secondary={item.value} />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 300, mx: 'auto' }}>
        <Button
          variant="contained"
          size="large"
          startIcon={<FolderIcon />}
          onClick={() => navigate(`/project-hub/projects/${projectId}`)}
          fullWidth
        >
          Go to Project Overview
        </Button>

        <Button
          variant="outlined"
          startIcon={<SettingsIcon />}
          onClick={() => navigate(`/portfolio-admin/companies/${companyId}`)}
          fullWidth
        >
          Go to Portfolio Admin
        </Button>

        <Button variant="outlined" startIcon={<HomeIcon />} onClick={() => navigate('/home')} fullWidth>
          Back to Home
        </Button>

        <Divider sx={{ my: 1 }} />

        <Button variant="text" onClick={onStartNew} size="small">
          Set up another project
        </Button>
      </Box>
    </Box>
  );
};

export default CompletionScreen;
