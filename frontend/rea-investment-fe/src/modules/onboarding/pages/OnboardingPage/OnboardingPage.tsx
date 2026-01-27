import React from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';

import { OnboardingProgress } from '../../components/OnboardingProgress/OnboardingProgress';
import { CompanyStep } from '../../components/CompanyStep/CompanyStep';
import { ProjectStep } from '../../components/ProjectStep/ProjectStep';
import { InviteStep } from '../../components/InviteStep/InviteStep';
import { CompletionScreen } from '../../components/CompletionScreen/CompletionScreen';
import { useOnboardingState } from '../../hooks/useOnboardingState';

export const OnboardingPage: React.FC = () => {
  const { state, isLoaded, setCompany, setProject, addInvitedUser, completeOnboarding, clearDraft, resetToStep } =
    useOnboardingState();

  const handleCompanyComplete = (companyId: number, companyName: string) => {
    setCompany(companyId, companyName);
  };

  const handleProjectComplete = (projectId: number, projectName: string) => {
    setProject(projectId, projectName);
  };

  const handleInviteSuccess = (email: string) => {
    addInvitedUser(email);
  };

  const handleInviteComplete = () => {
    completeOnboarding();
  };

  const handleStartNew = () => {
    clearDraft();
  };

  const handleBackToCompany = () => {
    resetToStep('company');
  };

  const handleBackToProject = () => {
    resetToStep('project');
  };

  if (!isLoaded) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  const renderStep = () => {
    switch (state.currentStep) {
      case 'company':
        return <CompanyStep onComplete={handleCompanyComplete} />;

      case 'project':
        if (!state.companyId || !state.companyName) {
          resetToStep('company');
          return null;
        }
        return (
          <ProjectStep
            companyId={state.companyId}
            companyName={state.companyName}
            onComplete={handleProjectComplete}
            onBack={handleBackToCompany}
          />
        );

      case 'invite':
        if (!state.companyId || !state.companyName || !state.projectId || !state.projectName) {
          resetToStep(state.companyId ? 'project' : 'company');
          return null;
        }
        return (
          <InviteStep
            companyId={state.companyId}
            companyName={state.companyName}
            projectId={state.projectId}
            projectName={state.projectName}
            invitedEmails={state.invitedUserEmails}
            onInviteSuccess={handleInviteSuccess}
            onComplete={handleInviteComplete}
            onBack={handleBackToProject}
          />
        );

      case 'complete':
        if (!state.companyId || !state.companyName || !state.projectId || !state.projectName) {
          resetToStep('company');
          return null;
        }
        return (
          <CompletionScreen
            companyId={state.companyId}
            companyName={state.companyName}
            projectId={state.projectId}
            projectName={state.projectName}
            invitedCount={state.invitedUserEmails.length}
            onStartNew={handleStartNew}
          />
        );

      default:
        return <CompanyStep onComplete={handleCompanyComplete} />;
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          {state.currentStep === 'complete' ? 'All Done!' : 'Set Up Your Project'}
        </Typography>
        {state.currentStep !== 'complete' && (
          <Typography variant="body1" color="text.secondary">
            Complete these steps to configure your project in Ilios
          </Typography>
        )}
      </Box>

      {state.currentStep !== 'complete' && (
        <OnboardingProgress
          currentStep={state.currentStep}
          companyName={state.companyName}
          projectName={state.projectName}
        />
      )}

      <Paper elevation={0} sx={{ p: 4, bgcolor: 'background.default' }}>
        {renderStep()}
      </Paper>
    </Container>
  );
};

export const createOnboardingHandle = () => ({
  breadcrumb: 'Setup'
});

export default OnboardingPage;
