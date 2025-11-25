import React from 'react';
import Avatar from '@mui/material/Avatar';
import PersonIcon from '@mui/icons-material/Person';

interface AssigneeProps {
  user: null | {
    id: number;
    first_name: string;
    last_name: string;
  };
}

export const Assignee: React.FC<AssigneeProps> = ({ user }) => (
  <Avatar
    sx={{
      width: 30,
      height: 30,
      fontSize: '12px',
      fontWeight: '600',
      backgroundColor: theme => theme.color.blueGray,
      lineHeight: '20px'
    }}
    data-testid="assignee__component"
    title={user ? `Assigned to: ${user.first_name} ${user.last_name}` : 'Unassigned'}
  >
    {user ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}` : <PersonIcon />}
  </Avatar>
);

export default Assignee;
