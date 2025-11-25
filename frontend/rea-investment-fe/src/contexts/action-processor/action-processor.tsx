import React from 'react';
import { useMutation } from '@tanstack/react-query';
import { noop } from 'lodash';
import { ApiClient } from '../../api';
import { AxiosError } from 'axios';

type SuccessHandler = (message: string) => void;
type ErrorHandler = SuccessHandler;
type SettledHandler = () => void;
type ActionProcessor = (
  id: number,
  onSuccess: SuccessHandler,
  onError: ErrorHandler,
  onSettled: SettledHandler
) => void;

interface ActionProcessors {
  userResendInviteProcessor: ActionProcessor;
}

interface Action {
  entityId: number;
  onSuccess: SuccessHandler;
  onError: ErrorHandler;
  onSettled: SettledHandler;
}

const ActionProcessorsContext = React.createContext<ActionProcessors | undefined>(undefined);

export const ActionProcessorsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [userResendInviteQueue, updateUserResendInviteQueue] = React.useState<Action[]>([]);

  const { isPending, mutate } = useMutation({
    mutationFn: ApiClient.user.resendInvite
  });

  React.useEffect(() => {
    if (!isPending && userResendInviteQueue.length > 0) {
      const action = userResendInviteQueue[userResendInviteQueue.length - 1];
      const { entityId, onError, onSuccess, onSettled } = action;
      mutate(entityId, {
        onSuccess: ({ message }) => onSuccess(message),
        onError: e => onError(e instanceof AxiosError ? e.response?.data?.message : e.message || e.message),
        onSettled: onSettled
      });
      const actionIndex = userResendInviteQueue.indexOf(action);
      updateUserResendInviteQueue(userResendInviteQueue.filter((_, i) => i !== actionIndex));
    }
  }, [isPending, userResendInviteQueue, mutate]);

  const userResendInviteProcessor = React.useCallback(
    (id: number, onSuccess: SuccessHandler, onError: ErrorHandler, onSettled: SettledHandler) => {
      updateUserResendInviteQueue(queue => [...queue, { entityId: id, onSuccess, onError, onSettled }]);
    },
    [updateUserResendInviteQueue]
  );

  const value = React.useMemo<ActionProcessors>(
    () => ({
      userResendInviteProcessor
    }),
    [userResendInviteProcessor]
  );

  return <ActionProcessorsContext.Provider value={value}>{children}</ActionProcessorsContext.Provider>;
};

export const useActionProcessor = (entity: 'user', action: 'resend-invite'): ActionProcessor => {
  const context = React.useContext(ActionProcessorsContext);

  if (context === undefined)
    throw new Error('ActionProcessorsContext is available only within the scope of ActionProcessorsProvider');

  const actionProcessor = React.useMemo<ActionProcessor>(() => {
    if (entity === 'user' && action === 'resend-invite') return context.userResendInviteProcessor;

    return noop;
  }, [entity, action, context]);

  return actionProcessor;
};
