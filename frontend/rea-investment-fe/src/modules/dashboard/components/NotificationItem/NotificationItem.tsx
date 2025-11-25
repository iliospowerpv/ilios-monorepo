import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import Avatar from '@mui/material/Avatar';
import PersonIcon from '@mui/icons-material/Person';
import CloseIcon from '@mui/icons-material/Close';
import CircleIcon from '@mui/icons-material/Circle';
import Stack from '@mui/material/Stack';
import IconButton from '@mui/material/IconButton';
import { styled } from '@mui/system';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';

import { ApiClient, FileDataResponse, Notification } from '../../../../api';
import useParsedComment from '../../../../hooks/common/useParsedComment';
import { BootstrapTooltip } from '../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { useQueryClient } from '@tanstack/react-query';

dayjs.extend(CustomParseFormatPlugin);

interface TemplateProps {
  notification: Notification;
  onClick?: () => void;
}

interface NotificationItemProps {
  loadMore: boolean;
  notification: Notification;
}

interface CustomListItemProps {
  isRead: boolean;
}

const formatDate = (date: string) => {
  return dayjs.utc(date).local().format('MM/DD/YY hh:mm:ss A');
};

const CustomListItem = styled(ListItem, { shouldForwardProp: prop => prop !== 'isRead' })<CustomListItemProps>(
  ({ isRead }) => ({
    backgroundColor: isRead ? '#fff' : '#25C1FC14',
    cursor: 'pointer',
    borderBottom: '1px solid #E0E0E0',
    transition: 'opacity 0.5s ease, transform 0.5s ease',
    '&:hover': {
      backgroundColor: isRead ? '#0000000a' : '#25C1FC29',
      boxShadow: '2px 2px 8px 0px #00000014',
      transition: 'box-shadow 300ms cubic-bezier(0.4, 0, 0.2, 1)'
    }
  })
);

const AvatarComponent: React.FC<TemplateProps> = ({ notification }) => {
  return (
    <ListItemAvatar sx={{ minWidth: '44px' }}>
      <Avatar
        sx={{
          width: '32px',
          height: '32px',
          fontSize: '12px',
          fontWeight: '700',
          backgroundColor: theme => theme.color.blueGray,
          lineHeight: '24px'
        }}
      >
        {notification.actor ? (
          `${notification.actor.first_name.charAt(0)}${notification.actor.last_name.charAt(0)}`
        ) : (
          <PersonIcon />
        )}
      </Avatar>
    </ListItemAvatar>
  );
};

const StatusChangeTemplate: React.FC<TemplateProps> = ({ notification }) => {
  return (
    <>
      <Typography variant="body1" mb="6px" fontSize="14px">
        The status of task <b>{notification.task.external_id}</b> has been changed to{' '}
        <b>{notification?.extra?.status}</b> by{' '}
        <b>
          {notification.actor.first_name} {notification.actor.last_name}
        </b>
        .
      </Typography>
    </>
  );
};

const AssigneeAddedTemplate: React.FC<TemplateProps> = ({ notification }) => {
  return (
    <>
      <Typography variant="body1" mb="6px" fontSize="14px">
        A new task <b>{notification.task.external_id}</b> has been assigned to you by{' '}
        <b>
          {notification.actor.first_name} {notification.actor.last_name}
        </b>
        . Please review and take the necessary actions.
      </Typography>
    </>
  );
};

const AssigneeChangedTemplate: React.FC<TemplateProps> = ({ notification }) => {
  return (
    <>
      <Typography variant="body1" mb="6px" fontSize="14px">
        The assignee for task <b>{notification.task.external_id}</b> has been changed to{' '}
        <b>{notification.extra?.new_assignee || 'Deleted User'}</b>.
      </Typography>
    </>
  );
};

const AssigneeUnsetTemplate: React.FC<TemplateProps> = ({ notification }) => {
  return (
    <>
      <Typography variant="body1" mb="6px" fontSize="14px">
        The assignee for task <b>{notification.task.external_id}</b> has been removed, and a new assignee has not yet
        been defined.
      </Typography>
      <Typography variant="body2" mb="4px" fontSize="12px">
        <b>Previous Assignee</b>: {notification.extra?.previous_assignee || 'Deleted User'}
      </Typography>
    </>
  );
};

const MentionTemplate: React.FC<TemplateProps> = ({ notification }) => {
  const { parsedComment, mentionTagClassname } = useParsedComment(notification?.comment?.text || '');
  return (
    <>
      <Typography variant="body1" fontSize="14px">
        You’ve been mentioned by{' '}
        <b>
          {notification.actor.first_name} {notification.actor.last_name}
        </b>{' '}
        in the system. Please take a moment to review the details below:
      </Typography>
      <Typography
        variant="body2"
        mb="4px"
        sx={{
          whiteSpace: 'pre-wrap',
          overflowWrap: 'break-word',
          [`& .${mentionTagClassname}`]: {
            borderRadius: '10px',
            px: '6px',
            paddingBottom: '2px',
            paddingTop: '0px',
            position: 'relative',
            fontWeight: '400',
            backgroundColor: '#1D1D1D',
            color: '#FFFFFF'
          }
        }}
        dangerouslySetInnerHTML={{ __html: parsedComment }}
      />
    </>
  );
};

const NotificationItem: React.FC<NotificationItemProps> = ({ notification }) => {
  const notify = useNotify();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleEventClick = React.useCallback(
    (notification: Notification) => {
      if (notification.kind === 'comment_mention') {
        if (notification.comment?.entity_type === 'document_key' && notification.extra) {
          navigate(
            `/due-diligence/companies/${notification.company.id}/sites/${notification.site.id}/due-diligence/${notification.extra.document_id}/?fileId=${notification.extra.file_id}`
          );
          return;
        } else if (notification.comment?.entity_type === 'document') {
          navigate(
            `/due-diligence/companies/${notification.company.id}/sites/${notification.site.id}/due-diligence/${notification.comment.entity_id}`
          );
          return;
        }
      }
      if (notification?.task?.module === 'O&M') {
        if (notification?.site) {
          navigate(
            `/operations-and-maintenance/companies/${notification.company.id}/sites/${notification.site.id}/tasks/${notification.task.id}`
          );
          return;
        } else {
          navigate(`/operations-and-maintenance/companies/${notification.company.id}/tasks/${notification.task.id}`);
          return;
        }
      }
      if (notification.site) {
        navigate(
          `/asset-management/companies/${notification.company.id}/sites/${notification.site.id}/tasks/${notification.task.id}`
        );
        return;
      } else {
        navigate(`/asset-management/companies/${notification.company.id}/tasks/${notification.task.id}`);
        return;
      }
    },
    [navigate]
  );

  const handleMarkAsRead = (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    event.stopPropagation();

    if (notification) {
      ApiClient.dashboard
        .markAsReadNotification(notification.id)
        .then((response: FileDataResponse) => {
          queryClient.invalidateQueries({ queryKey: ['notification'] });
          notify(response.message || '"Notification has been successfully marked as read"');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot marked as read notification');
        });
    }
  };

  const handleDelete = (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    event.stopPropagation();

    if (notification) {
      ApiClient.dashboard
        .deleteNotification(notification.id)
        .then((response: FileDataResponse) => {
          queryClient.invalidateQueries({ queryKey: ['notification'] });
          notify(response.message || 'Notification has been successfully removed');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Failed to delete notification. Please try again.');
        });
    }
  };

  return (
    <CustomListItem
      alignItems="flex-start"
      data-testid="notification-item__component"
      isRead={notification.seen}
      onClick={() => handleEventClick(notification)}
    >
      <AvatarComponent notification={notification} />
      <Box flexGrow="1">
        {notification.kind === 'task_status_change' && <StatusChangeTemplate notification={notification} />}
        {notification.kind === 'task_assignee_added' && <AssigneeAddedTemplate notification={notification} />}
        {notification.kind === 'task_assignee_changed' && <AssigneeChangedTemplate notification={notification} />}
        {notification.kind === 'task_assignee_unset' && <AssigneeUnsetTemplate notification={notification} />}
        {notification.kind === 'comment_mention' && <MentionTemplate notification={notification} />}
        <Typography variant="body2" mb="4px" fontSize="12px">
          <b>Company</b>: {notification.company?.name}{' '}
          {notification.site?.name && (
            <span>
              | <b>Site</b>: {notification.site.name}
            </span>
          )}
        </Typography>
        <Typography variant="body2" mb="4px" fontSize="12px">
          <b>Assigned on</b>: {formatDate(notification.created_at)}
        </Typography>
      </Box>
      <Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {!notification.seen && (
            <BootstrapTooltip title="Mark as Read" placement="top">
              <IconButton aria-label="circle" onClick={handleMarkAsRead}>
                <CircleIcon sx={{ color: '#20AFE3', fontSize: '14px' }} />
              </IconButton>
            </BootstrapTooltip>
          )}
          <BootstrapTooltip title="Delete" placement="top">
            <IconButton aria-label="close" onClick={handleDelete}>
              <CloseIcon sx={{ fontSize: '20px' }} />
            </IconButton>
          </BootstrapTooltip>
        </Stack>
      </Box>
    </CustomListItem>
  );
};

export default NotificationItem;
