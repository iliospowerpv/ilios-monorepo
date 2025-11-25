import { styled } from '@mui/material/styles';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import Modal from '@mui/material/Modal';

export const DocunentPreviewModal = styled(Modal)(() => ({
  '& .MuiDialogContent-root': {
    padding: 0
  }
}));

export const DocunentPreviewModalViewbox = styled(Box)(() => ({
  display: 'flex',
  height: '100%',
  outline: '0px',
  justifyContent: 'center',
  alignItems: 'center',
  minWidth: '600px'
}));

export const DocunentPreviewModalContent = styled(Box)(({ theme }) => ({
  [theme.breakpoints.between('xs', 'md')]: {
    width: 'calc(100% - 32px)'
  },
  [theme.breakpoints.between('md', 'lg')]: {
    width: 'calc(100% - 64px)'
  },
  [theme.breakpoints.between('lg', 'xl')]: {
    width: '90%'
  },
  [theme.breakpoints.up('xl')]: {
    width: '85%'
  },
  height: 'calc(100% - 32px)',
  minWidth: '600px',
  maxWidth: '2000px',
  margin: 'auto'
}));

export const DocumentPreviewContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  width: '100%',
  margin: '0 auto',
  '#proxy-renderer': {
    overflow: 'hidden'
  },
  '#pdf-controls': {
    position: 'absolute',
    width: '100%',
    height: '56px',
    justifyContent: 'flex-start',
    alignItems: 'center',
    boxShadow: 'none',
    padding: '8px 20px',
    borderBottom: '1px solid #E0E0E0',
    background: theme.palette.common.white,
    '& > *': {
      color: theme.palette.text.secondary,
      boxShadow: 'none',
      margin: '0px 8px'
    },
    path: {
      fill: theme.palette.text.secondary
    },
    polygon: {
      fill: theme.palette.text.secondary
    }
  },
  '#pdf-pagination': {
    order: 1,
    margin: 0,
    '& > *': {
      color: theme.palette.text.secondary,
      boxShadow: 'none'
    }
  },
  '#pdf-download': {
    display: 'none'
  },
  '#msdoc-renderer': {
    marginTop: '-1px',
    marginLeft: '-1px'
  }
}));

export const SubHeader = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: 0,
  width: '100%',
  marginLeft: 'auto',
  marginRight: 'auto',
  left: 0,
  right: 0,
  maxWidth: '2000px',
  height: '55px',
  padding: '8px 20px',
  borderBottom: '1px solid #E0E0E0',
  backgroundColor: theme.palette.common.white
}));

export const TermName = styled(Typography)(({ theme }) => ({
  color: theme.palette.text.secondary,
  fontWeight: 700,
  fontSize: '12px',
  textTransform: 'uppercase'
}));

export const AIResponseContainer = styled(Box)(() => ({
  padding: '12px',
  paddingBottom: '32px',
  marginBottom: '16px',
  position: 'relative'
}));

interface AITextProps {
  bgColor?: boolean | undefined;
}

export const AIText = styled(Box)<AITextProps>(({ theme, bgColor }) => ({
  backgroundColor: bgColor ? '#BDBDBD' : '#F0F0F0',
  color: theme.palette.text.secondary,
  scrollbarColor: bgColor ? `${theme.palette.text.secondary} #BDBDBD` : `${theme.palette.text.secondary} #F0F0F0`,
  minHeight: '24px',
  maxHeight: bgColor ? '170px' : '120px',
  overflowY: 'auto',
  overflowX: 'hidden',
  lineHeight: '24px',
  fontSize: '16px',
  textWrap: 'wrap',
  wordBreak: 'break-word'
}));

export const AccordionStyled = styled(Accordion)(({ expanded }) => ({
  boxShadow: 'none',
  border: '1px solid #E0E0E0',
  marginBottom: '16px',
  ...(!expanded && { borderBottom: 0 }),
  '&:before': {
    background: 'none'
  }
}));

export const AccordionSummaryStyled = styled(AccordionSummary)(() => ({
  borderBottom: '1px solid #E0E0E0',
  backgroundColor: 'rgba(0, 0, 0, 0.04)'
}));

export const DialogTitleStyled = styled(DialogTitle)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.secondary.main,
  position: 'relative',
  height: '90px',
  maxWidth: '100%',
  minWidth: '600px'
}));

export const DialogContentStyled = styled(DialogContent)(({ theme }) => ({
  backgroundColor: theme.palette.background.default,
  height: 'calc(100% - 90px)',
  flex: 0,
  overflow: 'unset',
  width: '100%',
  minWidth: '600px',
  position: 'relative'
}));
