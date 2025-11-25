import React from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Zoom from '@mui/material/Zoom';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import DescriptionIcon from '@mui/icons-material/Description';
import CheckIcon from '@mui/icons-material/Check';
import ImageIcon from '@mui/icons-material/Image';
import { styled } from '@mui/material/styles';

import { FileItem } from '../../../api';
import { BootstrapTooltip } from '../BootstrapTooltip/BootstrapTooltip';

dayjs.extend(utc);

export const Item = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  display: 'flex',
  cursor: 'pointer',
  flexDirection: 'row',
  alignItems: 'center',
  height: '86px',
  borderRadius: '4px',
  position: 'relative',
  overflow: 'hidden',
  boxShadow: '2px 2px 8px 0px #00000014',
  '&:hover': {
    backgroundColor: theme.palette.background.default
  }
}));

export const TypeContainer = styled(Box)(() => ({
  display: 'flex',
  flexDirection: 'column',
  borderRadius: '4px',
  backgroundColor: '#0000000A',
  alignItems: 'center',
  justifyContent: 'center',
  width: '48px',
  height: '48px'
}));

export const Checkmark = styled(Box)(() => ({
  position: 'absolute',
  bottom: 0,
  right: 0,
  width: '32px',
  height: '32px',
  padding: '1px',
  backgroundColor: '#20AFE3',
  clipPath: 'polygon(100% 0, 0% 100%, 100% 100%)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'end',
  justifyContent: 'end'
}));

interface DocumentProps {
  open: boolean;
  file: any;
  handleModalOpen: (file: FileItem) => void;
  handleMenuClick: (event: React.MouseEvent<HTMLElement>, file: FileItem) => void;
}

const Document: React.FC<DocumentProps> = props => {
  const { open, file, handleModalOpen, handleMenuClick } = props;

  const formatDate = (date: string) => {
    return dayjs.utc(date).local().format('MMMM DD YYYY, h:mm A');
  };

  if (!file) return null;

  return (
    <Item onClick={() => handleModalOpen(file)}>
      <TypeContainer>
        {['jpg', 'jpeg', 'png'].includes(file.extension) ? (
          <ImageIcon sx={{ fontSize: '18px', color: theme => theme.color.blueGray }} />
        ) : (
          <DescriptionIcon sx={{ fontSize: '18px', color: file.extension === 'pdf' ? '#C62828' : '#2757FF' }} />
        )}
        <Typography variant="caption" fontSize="10px" lineHeight="14px" fontWeight="500">
          {file.extension.toUpperCase()}
        </Typography>
      </TypeContainer>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          pl: 1,
          width: '75%',
          '@media (min-width: 1280px)': {
            width: '80%'
          }
        }}
      >
        <Typography
          variant="body2"
          fontSize="16px"
          lineHeight="24px"
          sx={{
            width: '100%',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
        >
          {file.filename}
        </Typography>
        <Typography variant="caption" fontSize="12px" lineHeight="20px" color="text.secondary">
          {formatDate(file.created_at)}
        </Typography>
      </Box>
      <IconButton
        id={`basic-button`}
        aria-controls={open ? `basic-menu` : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={e => handleMenuClick(e, file)}
        sx={{ position: 'absolute', top: '4px', right: '4px' }}
      >
        <MoreVertIcon />
      </IconButton>
      <Zoom in={file.is_actual}>
        <Checkmark>
          <BootstrapTooltip title="Actual" placement="bottom">
            <CheckIcon sx={{ fontSize: '18px', color: theme => theme.palette.common.white }} />
          </BootstrapTooltip>
        </Checkmark>
      </Zoom>
    </Item>
  );
};

export default Document;
