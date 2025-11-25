import React from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import Stack from '@mui/material/Stack';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import useParsedComment from '../../../hooks/common/useParsedComment';

dayjs.extend(utc);

const avatarStyles = {
  width: 40,
  height: 40,
  marginTop: '8px !important',
  backgroundColor: (theme: { color: { blueGray: any } }) => theme.color.blueGray,
  fontSize: '14px',
  fontWeight: '600'
};

interface CommentListItemProps {
  user: {
    first_name: string;
    last_name: string;
  };
  date: string;
  text: string;
}

const CommentListItem: React.FC<CommentListItemProps> = ({ user, date, text }) => {
  const formattedDate = dayjs.utc(date).local().format('MMMM D, YYYY, h:mm A');

  const { parsedComment, mentionTagClassname } = useParsedComment(text);

  return (
    <Stack direction="row" spacing={2} flexWrap="nowrap" pb={t => t.spacing(2)}>
      <Avatar data-testid="comment-list-item_avatar" sx={avatarStyles} alt={user.first_name + ' ' + user.last_name}>
        {user.first_name.charAt(0) + user.last_name.charAt(0)}
      </Avatar>
      <Box>
        <Stack
          direction="row"
          flexWrap="wrap"
          sx={{
            color: theme => theme.palette.text.secondary,
            '& > *:not(:last-child)': { mr: theme => theme.spacing(1) }
          }}
        >
          <Typography component="span" variant="body2" fontWeight="600">
            {user.first_name + ' ' + user.last_name}
          </Typography>
          <Typography component="span" variant="body2">
            {formattedDate}
          </Typography>
        </Stack>
        <Box sx={{ overflow: 'hidden', wordBreak: 'break-word' }}>
          <Typography
            variant="body1"
            component="p"
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
        </Box>
      </Box>
    </Stack>
  );
};

export default CommentListItem;
