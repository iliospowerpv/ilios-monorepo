import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiClient, Recovery, ResetSetupData } from '../../api';

export const useReset = () => {
  const navigate = useNavigate();
  const mutation = useMutation<Recovery, Error, ResetSetupData>({
    mutationFn: ApiClient.passwordRecovery.resetSetup,
    onSuccess: () => {
      navigate('/password-reset-success');
    }
  });

  return {
    mutation
  };
};
