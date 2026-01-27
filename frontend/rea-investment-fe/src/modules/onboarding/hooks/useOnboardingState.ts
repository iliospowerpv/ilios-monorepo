import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../../../contexts/auth/auth';

export type OnboardingStep = 'company' | 'project' | 'invite' | 'complete';

export interface OnboardingDraftState {
  currentStep: OnboardingStep;
  companyId: number | null;
  companyName: string | null;
  projectId: number | null;
  projectName: string | null;
  invitedUserEmails: string[];
}

const STORAGE_KEY_PREFIX = 'ilios_onboarding_draft_';

const getStorageKey = (userId: number): string => `${STORAGE_KEY_PREFIX}${userId}`;

const defaultState: OnboardingDraftState = {
  currentStep: 'company',
  companyId: null,
  companyName: null,
  projectId: null,
  projectName: null,
  invitedUserEmails: []
};

export const useOnboardingState = () => {
  const { user } = useAuth();
  const userId = user?.id;

  const [state, setState] = useState<OnboardingDraftState>(defaultState);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!userId) {
      // If no user yet, still mark as loaded with default state
      setIsLoaded(true);
      return;
    }

    try {
      const stored = localStorage.getItem(getStorageKey(userId));
      if (stored) {
        const parsed = JSON.parse(stored) as OnboardingDraftState;
        setState(parsed);
      }
    } catch {
      // Ignore parse errors
    }
    setIsLoaded(true);
  }, [userId]);

  const saveState = useCallback(
    (newState: OnboardingDraftState) => {
      if (!userId) return;

      setState(newState);
      try {
        localStorage.setItem(getStorageKey(userId), JSON.stringify(newState));
      } catch {
        // Ignore storage errors
      }
    },
    [userId]
  );

  const setStep = useCallback(
    (step: OnboardingStep) => {
      saveState({ ...state, currentStep: step });
    },
    [state, saveState]
  );

  const setCompany = useCallback(
    (companyId: number, companyName: string) => {
      saveState({ ...state, companyId, companyName, currentStep: 'project' });
    },
    [state, saveState]
  );

  const setProject = useCallback(
    (projectId: number, projectName: string) => {
      saveState({ ...state, projectId, projectName, currentStep: 'invite' });
    },
    [state, saveState]
  );

  const addInvitedUser = useCallback(
    (email: string) => {
      if (!state.invitedUserEmails.includes(email)) {
        saveState({
          ...state,
          invitedUserEmails: [...state.invitedUserEmails, email]
        });
      }
    },
    [state, saveState]
  );

  const completeOnboarding = useCallback(() => {
    saveState({ ...state, currentStep: 'complete' });
  }, [state, saveState]);

  const clearDraft = useCallback(() => {
    if (!userId) return;

    setState(defaultState);
    try {
      localStorage.removeItem(getStorageKey(userId));
    } catch {
      // Ignore storage errors
    }
  }, [userId]);

  const resetToStep = useCallback(
    (step: OnboardingStep) => {
      const newState: OnboardingDraftState = { ...defaultState };

      if (step === 'project' || step === 'invite' || step === 'complete') {
        newState.companyId = state.companyId;
        newState.companyName = state.companyName;
      }
      if (step === 'invite' || step === 'complete') {
        newState.projectId = state.projectId;
        newState.projectName = state.projectName;
      }

      newState.currentStep = step;
      saveState(newState);
    },
    [state, saveState]
  );

  return {
    state,
    isLoaded,
    setStep,
    setCompany,
    setProject,
    addInvitedUser,
    completeOnboarding,
    clearDraft,
    resetToStep
  };
};
