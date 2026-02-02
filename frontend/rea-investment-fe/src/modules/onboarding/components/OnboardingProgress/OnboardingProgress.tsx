import React from 'react';
import Box from '@mui/material/Box';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Typography from '@mui/material/Typography';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { OnboardingStep } from '../../hooks/useOnboardingState';

interface OnboardingProgressProps {
  currentStep: OnboardingStep;
  companyName?: string | null;
  projectName?: string | null;
}

const steps = [
  { key: 'company', label: 'Company' },
  { key: 'project', label: 'Project' },
  { key: 'invite', label: 'Invite Users' }
];

const getStepIndex = (step: OnboardingStep): number => {
  switch (step) {
    case 'company':
      return 0;
    case 'project':
      return 1;
    case 'invite':
      return 2;
    case 'complete':
      return 3;
    default:
      return 0;
  }
};

export const OnboardingProgress: React.FC<OnboardingProgressProps> = ({ currentStep, companyName, projectName }) => {
  const activeStep = getStepIndex(currentStep);

  return (
    <Box sx={{ width: '100%', mb: 4 }}>
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((step, index) => {
          const isComplete = index < activeStep;
          const isCurrent = index === activeStep;

          let subtitle = '';
          if (step.key === 'company' && companyName && isComplete) {
            subtitle = companyName;
          } else if (step.key === 'project' && projectName && isComplete) {
            subtitle = projectName;
          } else if (step.key === 'invite' && isComplete) {
            subtitle = 'Done';
          }

          return (
            <Step key={step.key} completed={isComplete}>
              <StepLabel StepIconComponent={isComplete ? () => <CheckCircleIcon color="success" /> : undefined}>
                <Box>
                  <Typography
                    variant="body2"
                    fontWeight={isCurrent ? 600 : 400}
                    color={isCurrent ? 'primary' : 'text.secondary'}
                  >
                    {step.label}
                  </Typography>
                  {subtitle && (
                    <Typography variant="caption" color="text.secondary">
                      {subtitle}
                    </Typography>
                  )}
                </Box>
              </StepLabel>
            </Step>
          );
        })}
      </Stepper>
    </Box>
  );
};

export default OnboardingProgress;
