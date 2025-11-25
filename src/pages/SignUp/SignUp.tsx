import React from 'react';
import { useLocation } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';

import { ApiClient } from '../../api';
import { SignUpFormScreen, BlankScreen, SignUpSuccesScreen, SignUpFailedScreen } from './screens';

import type { SignUpFormInputs, SignUpScreenProps } from './screens';
import { AxiosError } from 'axios';

enum RenderScreen {
  None = 'none',
  Form = 'form',
  Success = 'success',
  Failure = 'failure'
}

const SignUpPage: React.FC = () => {
  const location = useLocation();
  const queryParams = React.useMemo(() => new URLSearchParams(location.search), [location]);
  const renderScreenMap: Record<RenderScreen, React.FC<SignUpScreenProps>> = React.useMemo(
    () => ({
      [RenderScreen.None]: BlankScreen,
      [RenderScreen.Form]: SignUpFormScreen,
      [RenderScreen.Success]: SignUpSuccesScreen,
      [RenderScreen.Failure]: SignUpFailedScreen
    }),
    []
  );
  const [currentScreen, setCurrentScreen] = React.useState<RenderScreen>(RenderScreen.None);

  const email = queryParams.get('email') || '';
  const token = queryParams.get('token') || '';

  const { mutate: validateToken, error: validateTokenError } = useMutation({
    mutationFn: () => ApiClient.user.validateEmailToken(email, token, 'sign-up'),
    onSuccess: () => setCurrentScreen(RenderScreen.Form),
    onError: () => setCurrentScreen(RenderScreen.Failure)
  });

  React.useEffect(() => {
    validateToken();
  }, [validateToken]);

  const {
    mutateAsync: setUserAccountPassword,
    error: setUserAccountPasswordError,
    isPending: isSetUserAccountPasswordPending
  } = useMutation({
    mutationFn: (data: SignUpFormInputs) => ApiClient.user.setupPassword(email, token, data.password, 'sign-up'),
    onSuccess: () => setCurrentScreen(RenderScreen.Success),
    onError: () => setCurrentScreen(RenderScreen.Failure)
  });

  const submitSetUserPassword = React.useCallback(
    async (data: SignUpFormInputs) => {
      await setUserAccountPassword(data).catch(e => e);
    },
    [setUserAccountPassword]
  );

  const ScreenToRender = renderScreenMap[currentScreen];

  const failureReason =
    (!!validateTokenError && 'An error occured when trying to validate your sign-up link') ||
    (!!setUserAccountPasswordError && 'Something when wrong when submitting the form') ||
    '';

  return (
    <ScreenToRender
      email={email}
      token={token}
      failureReason={failureReason}
      errorMessage={
        (validateTokenError instanceof AxiosError && validateTokenError.response?.data?.message) ||
        validateTokenError?.message ||
        (setUserAccountPasswordError instanceof AxiosError && setUserAccountPasswordError.response?.data?.message) ||
        setUserAccountPasswordError?.message ||
        ''
      }
      formSubmit={submitSetUserPassword}
      isSubmitPending={isSetUserAccountPasswordPending}
    />
  );
};

export default SignUpPage;
