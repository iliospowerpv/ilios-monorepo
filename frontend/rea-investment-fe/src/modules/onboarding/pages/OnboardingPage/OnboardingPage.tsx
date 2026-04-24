import React, { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';

import { OnboardingProgress } from '../../components/OnboardingProgress/OnboardingProgress';
import { CompanyStep } from '../../components/CompanyStep/CompanyStep';
import { ProjectStep } from '../../components/ProjectStep/ProjectStep';
import { InviteStep } from '../../components/InviteStep/InviteStep';
import { CompletionScreen } from '../../components/CompletionScreen/CompletionScreen';
import { useOnboardingState } from '../../hooks/useOnboardingState';
import { ApiClient } from '../../../../api';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';

export const OnboardingPage: React.FC = () => {
  const { state, isLoaded, setCompany, setProject, addInvitedUser, completeOnboarding, clearDraft, resetToStep } =
    useOnboardingState();
  const { setCurrentCompany } = useEntityContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlCompanyId = searchParams.get('companyId');
  const parsedUrlCompanyId = urlCompanyId ? Number(urlCompanyId) : null;
  const validUrlCompanyId =
    parsedUrlCompanyId !== null && Number.isInteger(parsedUrlCompanyId) && parsedUrlCompanyId > 0
      ? parsedUrlCompanyId
      : null;

  const workspaceQuery = useQuery({
    queryKey: ['workspace', 'onboarding-bootstrap'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    enabled: validUrlCompanyId !== null,
    staleTime: 60 * 1000
  });

  const bootstrappedRef = useRef<number | null>(null);
  const [bootstrapError, setBootstrapError] = React.useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || validUrlCompanyId === null) return;
    if (bootstrappedRef.current === validUrlCompanyId) return;
    if (workspaceQuery.isLoading) return;

    if (workspaceQuery.isError) {
      bootstrappedRef.current = validUrlCompanyId;
      setBootstrapError("We couldn't load your companies. Please pick one below.");
      setSearchParams({}, { replace: true });
      return;
    }

    const companies = workspaceQuery.data?.companies ?? [];
    const matched = companies.find((c) => c.company_id === validUrlCompanyId);

    if (!matched) {
      bootstrappedRef.current = validUrlCompanyId;
      setBootstrapError("That company isn't available to you. Please pick one below.");
      setSearchParams({}, { replace: true });
      return;
    }

    bootstrappedRef.current = validUrlCompanyId;

    setCurrentCompany({ id: matched.company_id, name: matched.company_name });

    if (state.companyId !== matched.company_id) {
      clearDraft();
      setCompany(matched.company_id, matched.company_name);
    } else if (state.currentStep === 'company') {
      setCompany(matched.company_id, matched.company_name);
    }

    setSearchParams({}, { replace: true });
  }, [
    isLoaded,
    validUrlCompanyId,
    workspaceQuery.isLoading,
    workspaceQuery.isError,
    workspaceQuery.data,
    state.companyId,
    state.currentStep,
    setCompany,
    clearDraft,
    setCurrentCompany,
    setSearchParams
  ]);

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

      {bootstrapError && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setBootstrapError(null)}>
          {bootstrapError}
        </Alert>
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
