import React from 'react';
import { EventClickArg } from '@fullcalendar/core';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import PersonIcon from '@mui/icons-material/Person';
import { useTheme } from '@mui/material/styles';
import FlagIcon from '@mui/icons-material/Flag';
import { styled } from '@mui/system';
import Box from '@mui/material/Box';

export const TaskContainer = styled(Box)(() => ({
  display: 'flex',
  border: '1px solid #0000001F',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'flex-start',
  padding: '6px',
  minHeight: '60px',
  width: '100%'
}));

export const Header = styled(Box)(() => ({
  height: '20px',
  width: '100%',
  marginBottom: '4px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between'
}));

export const Footer = styled(Box)(() => ({
  height: '24px',
  width: '100%',
  marginTop: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between'
}));

interface TaskProps {
  eventInfo: EventClickArg;
}

const Task: React.FC<TaskProps> = ({ eventInfo }) => {
  const { title, extendedProps } = eventInfo.event;
  const { efficiencyColors, color } = useTheme();
  const taskPriority: any = {
    High: <FlagIcon sx={{ color: efficiencyColors.low, marginRight: '8px' }} />,
    Low: <FlagIcon sx={{ color: efficiencyColors.good, marginRight: '8px' }} />,
    Medium: <FlagIcon sx={{ color: efficiencyColors.mediocre, marginRight: '8px' }} />
  };

  if (!eventInfo.event) return null;

  return (
    <TaskContainer className="custom-event" data-testid="calendar-view__task">
      <Header>
        <Typography variant="subtitle2" display="flex" fontWeight={600} fontSize="14px" lineHeight="24px">
          {taskPriority[extendedProps.priority]}
          <span>{extendedProps.externalId}</span>
        </Typography>
      </Header>
      <Typography
        variant="body2"
        sx={{
          fontWeight: 400,
          fontSize: '14px',
          lineHeight: '20px',
          marginBottom: '8px',
          wordWrap: 'break-word',
          whiteSpace: 'normal',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}
      >
        {title}
      </Typography>
      <Footer>
        <Chip
          label={extendedProps.status.name}
          size="small"
          sx={{
            color: theme => theme.palette.common.white,
            backgroundColor: theme => theme.palette.primary.main
          }}
        />
        <Avatar
          sx={{
            width: 24,
            height: 24,
            fontSize: '12px',
            fontWeight: '600',
            backgroundColor: color.blueGray,
            lineHeight: '20px'
          }}
          title={
            extendedProps.assignee
              ? `Assigned to: ${extendedProps.assignee.first_name} ${extendedProps.assignee.last_name}`
              : 'Unassigned'
          }
        >
          {extendedProps.assignee ? (
            `${extendedProps.assignee.first_name.charAt(0)}${extendedProps.assignee.last_name.charAt(0)}`
          ) : (
            <PersonIcon />
          )}
        </Avatar>
      </Footer>
    </TaskContainer>
  );
};

export default Task;
