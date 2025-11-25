import React from 'react';
import { ToastContainer, toast, Zoom } from 'react-toastify';
import SnackbarContent from '@mui/material/SnackbarContent';
import IconButton from '@mui/material/IconButton';
import CloseOutlinedIcon from '@mui/icons-material/CloseOutlined';
import 'react-toastify/dist/ReactToastify.css';
import { styled } from '@mui/material';

const StyledToastContainer = styled(ToastContainer)`
  &&&.Toastify__toast-container {
    left: 72px;
    max-width: 480px;
    width: auto;
  }
  .Toastify__toast {
    box-shadow: none;
    background: transparent;
    margin-bottom: 0;
  }
`;

const ToastBody: React.FC<{ closeToast: () => void; message: string }> = ({ closeToast, message }) => (
  <SnackbarContent
    sx={{ flexWrap: 'nowrap', flexDirection: 'row', backgroundColor: '#323232' }}
    message={message}
    action={
      <IconButton sx={{ mx: '8px' }} color="secondary" size="small" onClick={closeToast}>
        <CloseOutlinedIcon />
      </IconButton>
    }
  />
);

type NotifyFunc = (message: string) => void;

const NotificationsContext = React.createContext<NotifyFunc | undefined>(undefined);

export const NotificationsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const notify = React.useCallback<NotifyFunc>(message => {
    toast(({ closeToast }) => <ToastBody message={message} closeToast={closeToast} />);
  }, []);

  return (
    <>
      <NotificationsContext.Provider value={notify}>
        {children}
        <StyledToastContainer
          position="bottom-left"
          autoClose={5000}
          hideProgressBar
          closeButton={false}
          transition={Zoom}
        />
      </NotificationsContext.Provider>
    </>
  );
};

export const useNotify = (): NotifyFunc => {
  const context = React.useContext(NotificationsContext);

  if (context === undefined)
    throw new Error('NotificationsContext is available only within the scope of NotificationsProvider');

  return context;
};
