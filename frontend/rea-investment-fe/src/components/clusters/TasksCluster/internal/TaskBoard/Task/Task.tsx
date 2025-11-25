import React from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import FlagIcon from '@mui/icons-material/Flag';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import PersonIcon from '@mui/icons-material/Person';
import { Draggable, DraggableProvided } from 'react-beautiful-dnd';
import { useTheme } from '@mui/material/styles';

import { TaskContainer, Header, Footer } from '../TaskBoard.styles';
import { TaskType } from '../../../../../../api';

dayjs.extend(utc);

interface TaskProps {
  index: number;
  item: TaskType;
  onTaskClick: (id: number) => void;
}

const Task: React.FC<TaskProps> = ({ item, index, onTaskClick }) => {
  const { efficiencyColors } = useTheme();
  const taskPriority: any = {
    High: <FlagIcon sx={{ color: efficiencyColors.low, marginRight: '8px' }} />,
    Low: <FlagIcon sx={{ color: efficiencyColors.good, marginRight: '8px' }} />,
    Medium: <FlagIcon sx={{ color: efficiencyColors.mediocre, marginRight: '8px' }} />
  };
  const formatDate = (date: string) => dayjs.utc(date).local().format('MM/DD/YYYY');

  if (!item) return null;

  return (
    <Draggable key={item.id} draggableId={`${item.id}`} index={index}>
      {(provided: DraggableProvided) => (
        <div ref={provided.innerRef} {...provided.draggableProps} {...provided.dragHandleProps}>
          <TaskContainer onClick={() => onTaskClick(item.id)}>
            <Header>
              <Typography variant="subtitle2" display="flex" fontWeight={600} fontSize="14px" lineHeight="24px">
                {taskPriority[item.priority]}
                <span>{item.external_id}</span>
              </Typography>
              <Typography
                variant="body2"
                display="flex"
                fontWeight={400}
                fontSize="14px"
                lineHeight="24px"
                color="text.secondary"
              >
                {item.due_date === null ? 'No due date' : formatDate(item.due_date)}
              </Typography>
            </Header>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 400,
                fontSize: '14px',
                lineHeight: '20px',
                display: '-webkit-box',
                marginBottom: '8px',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
            >
              {item.name}
            </Typography>
            <Footer>
              <Avatar
                sx={{
                  width: 28,
                  height: 28,
                  fontSize: '12px',
                  fontWeight: '600',
                  backgroundColor: theme => theme.color.blueGray,
                  lineHeight: '20px'
                }}
                title={
                  item.assignee ? `Assigned to: ${item.assignee.first_name} ${item.assignee.last_name}` : 'Unassigned'
                }
              >
                {item.assignee ? (
                  `${item.assignee.first_name.charAt(0)}${item.assignee.last_name.charAt(0)}`
                ) : (
                  <PersonIcon />
                )}
              </Avatar>
            </Footer>
          </TaskContainer>
        </div>
      )}
    </Draggable>
  );
};

export default Task;
