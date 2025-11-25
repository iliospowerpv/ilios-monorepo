import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Collapse from '@mui/material/Collapse';
import CircularProgress from '@mui/material/CircularProgress';
import { styled } from '@mui/system';
import { TransitionGroup } from 'react-transition-group';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import NotificationItem from '../NotificationItem/NotificationItem';
import { ApiClient, Notification } from '../../../../api';

const NotificationListStyled = styled(Box)(() => ({
  display: 'flex',
  flexDirection: 'column',
  flexGrow: 1,
  padding: '16px 0 0',
  marginTop: '8px',
  border: '1px solid #0000003B',
  maxHeight: 'calc(100vh - 160px)',
  overflowY: 'auto'
}));

export const NotificationList: React.FC = () => {
  const [loadMore, setLoadMore] = useState(false);

  const { data: notificationsData, isFetching: isFetchingNotificationsData } = useQuery({
    queryFn: async () => {
      return ApiClient.dashboard.getDashboardNotifications({
        skip: 0,
        limit: loadMore ? 100 : 5
      });
    },
    queryKey: ['notification', { showMore: loadMore }],
    placeholderData: keepPreviousData
  });

  const notifications = notificationsData;
  const isShowMore = !loadMore && !!notifications?.items?.length && notifications?.total > 5;

  const handleShowMoreClick = () => {
    setLoadMore(true);
  };

  return (
    <NotificationListStyled data-testid="notification-list__component">
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="h6" fontSize="24px" paddingLeft="16px" mb="8px">
          Notifications
        </Typography>
        {!!notifications?.unread_count && (
          <Chip
            label={`${notifications?.unread_count} New`}
            size="small"
            variant="outlined"
            sx={{ borderColor: '#20AFE3', padding: '3px 4px', fontSize: '13px' }}
          />
        )}
      </Stack>
      <List
        sx={{ width: '100%', bgcolor: 'background.paper', paddingBottom: 0, position: 'relative', display: 'flex' }}
      >
        {notifications?.items?.length ? (
          <TransitionGroup>
            {notifications?.items?.map((notification: Notification) => (
              <Collapse key={notification.id}>
                <NotificationItem notification={notification} loadMore={loadMore} />
              </Collapse>
            ))}
          </TransitionGroup>
        ) : (
          <Box
            sx={{
              margin: '16px auto',
              height: '140px',
              py: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {!isFetchingNotificationsData && (
              <Typography variant="body1" textAlign="center" mb="8px">
                No notifications to show
              </Typography>
            )}
          </Box>
        )}
        {isFetchingNotificationsData && (
          <Box
            sx={{
              position: 'absolute',
              width: '100%',
              height: 'calc(100% - 8px)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              flexDirection: 'column',
              backgroundColor: notifications?.items?.length ? 'rgb(0 0 0 / .1)' : 'transparent'
            }}
          >
            <CircularProgress />
          </Box>
        )}
      </List>
      {isShowMore && (
        <Box bgcolor="rgba(255, 255, 255, 0.85)" p="16px">
          <Link component="button" variant="body2" underline="hover" fontWeight={600} onClick={handleShowMoreClick}>
            Show More
          </Link>
        </Box>
      )}
    </NotificationListStyled>
  );
};

export default NotificationList;
