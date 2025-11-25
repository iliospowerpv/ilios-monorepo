import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiClient, Recovery, ResetRequestData } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';

export const useResetRequest = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const mutation = useMutation<Recovery, Error, ResetRequestData>({
    mutationFn: ApiClient.passwordRecovery.resetRequest,
    onSuccess: (data: any, variables: { email: string }) => {
      notify('Email with password reset instructions was sent');
      navigate('/reset-notification', { state: { email: variables?.email } });
    }
  });

  return {
    mutation
  };
};
