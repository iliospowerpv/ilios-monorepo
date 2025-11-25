import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiClient, UserAuth, UserLoginData } from '../../api';

export const useAuthLogin = () => {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const mutation = useMutation<UserAuth, Error, UserLoginData>({
    mutationFn: ApiClient.user.login,
    onSuccess: data => {
      ApiClient._tokenManager.updateAuthToken(data.access_token);
      navigate('/dashboard');
    },
    onError: (error: any) => {
      setServerError(error?.response?.data?.message || 'Something went wrong ...');
    }
  });

  return {
    mutation,
    serverError
  };
};
