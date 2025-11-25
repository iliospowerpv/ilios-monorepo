import React from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import LinkIcon from '@mui/icons-material/Link';
import MarkunreadIcon from '@mui/icons-material/Markunread';
import { useNavigate } from 'react-router-dom';
import { useActionProcessor } from '../../../../../contexts/action-processor/action-processor';
import { useNotify } from '../../../../../contexts/notifications/notifications';

interface ActionButtonsProps {
  data: any;
  isAdd?: boolean;
  isEdit?: boolean;
  isLink?: boolean;
  isDelete?: boolean;
  isRegistered: boolean;
  onAdd?: string;
  onEdit?: string;
  onLink?: string;
  onDelete?: (data: any) => void;
  hideEditActions?: boolean;
}

const ActionButtons: React.FC<ActionButtonsProps> = props => {
  const { data, isAdd, isEdit, isLink, isDelete, isRegistered, onAdd, onEdit, onLink, onDelete, hideEditActions } =
    props;
  const navigate = useNavigate();
  const notify = useNotify();
  const [resendInProgress, setResendInProgress] = React.useState(false);
  const processResendInvite = useActionProcessor('user', 'resend-invite');

  const onClickResend = () => {
    setResendInProgress(true);
    processResendInvite(data.id, notify, notify, () => setResendInProgress(false));
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        height: '40px',
        button: {
          mx: 0.5
        }
      }}
    >
      {!hideEditActions && (
        <>
          {isAdd && (
            <IconButton title="Add a New Site" onClick={() => onAdd && navigate(onAdd)} size="small">
              <AddIcon fontSize="small" />
            </IconButton>
          )}
          {isEdit && (
            <IconButton title="Edit" onClick={() => onEdit && navigate(onEdit)} size="small">
              <EditIcon fontSize="small" />
            </IconButton>
          )}
          {isLink && (
            <IconButton title="Connections" onClick={() => onLink && navigate(onLink)} size="small">
              <LinkIcon fontSize="small" />
            </IconButton>
          )}
          {isDelete && (
            <IconButton title="Delete" onClick={() => onDelete && onDelete(data)} size="small">
              <DeleteIcon fontSize="small" />
            </IconButton>
          )}
        </>
      )}
      {!isRegistered && (
        <IconButton title="Resend Invitation" disabled={resendInProgress} onClick={onClickResend} size="small">
          <MarkunreadIcon fontSize="small" />
        </IconButton>
      )}
    </Box>
  );
};

export default ActionButtons;
