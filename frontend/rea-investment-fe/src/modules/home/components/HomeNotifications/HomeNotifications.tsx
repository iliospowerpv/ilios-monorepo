import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Collapse from '@mui/material/Collapse';
import CircularProgress from '@mui/material/CircularProgress';
import { TransitionGroup } from 'react-transition-group';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import NotificationItem from '../../../dashboard/components/NotificationItem/NotificationItem';
import { ApiClient, Notification } from '../../../../api';

interface HomeNotificationsProps {
  onNotificationsLoaded?: (count: number) => void;
}

export const HomeNotifications: React.FC<HomeNotificationsProps> = ({ onNotificationsLoaded }) => {
  const [loadMore, setLoadMore] = useState(false);

  const { data: notificationsData, isFetching: isFetchingNotificationsData } = useQuery({
    queryFn: async () => {
      const result = await ApiClient.dashboard.getDashboardNotifications({
        skip: 0,
        limit: loadMore ? 100 : 5
      });
      if (onNotificationsLoaded) {
        onNotificationsLoaded(result.unread_count || 0);
      }
      return result;
    },
    queryKey: ['home-notifications', { showMore: loadMore }],
    placeholderData: keepPreviousData
  });

  const notifications = notificationsData;
  const isShowMore = !loadMore && !!notifications?.items?.length && notifications?.total > 5;

  const handleShowMoreClick = () => {
    setLoadMore(true);
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ borderBottom: theme => `1px solid ${theme.palette.divider}`, px: 2, py: 1.5 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6">Notifications</Typography>
            {!!notifications?.unread_count && (
              <Chip
                label={`${notifications?.unread_count} New`}
                size="small"
                variant="outlined"
                sx={{ borderColor: '#20AFE3', padding: '3px 4px', fontSize: '13px' }}
              />
            )}
          </Stack>
        </Box>

        <Box sx={{ flex: 1, overflow: 'auto', maxHeight: 300 }}>
          <List sx={{ width: '100%', bgcolor: 'background.paper', paddingBottom: 0, position: 'relative' }}>
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
                  height: '100px',
                  py: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {!isFetchingNotificationsData && (
                  <Typography variant="body1" textAlign="center" color="text.secondary">
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
        </Box>

        {isShowMore && (
          <Box bgcolor="rgba(255, 255, 255, 0.85)" p={2} borderTop={1} borderColor="divider">
            <Link component="button" variant="body2" underline="hover" fontWeight={600} onClick={handleShowMoreClick}>
              Show More
            </Link>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default HomeNotifications;
