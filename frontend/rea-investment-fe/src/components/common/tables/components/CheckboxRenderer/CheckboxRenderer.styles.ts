import { styled } from '@mui/system';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';

export const CheckIcon = styled(CheckCircleIcon)(() => ({
  fill: '#6CC469'
}));

export const CrossIcon = styled(CancelIcon)(() => ({
  fill: '#B02E0C'
}));

export const CellContainer = styled('div')(() => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: '100%'
}));
