import React from 'react';
import { styled } from '@mui/material/styles';
import TableCell from '@mui/material/TableCell';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import MenuItem from '@mui/material/MenuItem';
import Table from '@mui/material/Table';

interface TextBoxProps extends React.DetailedHTMLProps<React.HTMLAttributes<HTMLSpanElement>, HTMLSpanElement> {
  fieldName?: boolean;
}

export const FieldCell = styled(TableCell)(() => ({
  border: 'none',
  padding: '8px',
  paddingBottom: '0px',
  verticalAlign: 'middle',
  lineHeight: 1.57
}));

export const StyledSelectItem = styled(MenuItem)(() => ({
  fontSize: '0.875rem',
  lineHeight: 1.43
}));

export const TextBox = styled('span')<TextBoxProps>(({ fieldName }) => ({
  fontWeight: fieldName ? 600 : 400,
  overflow: 'hidden',
  textWrap: 'wrap',
  wordBreak: fieldName ? 'break-word' : 'break-all'
}));

export const DetailsContainer = styled(Box)(() => ({
  padding: '8px',
  border: '1px solid #0000003B'
}));

export const SectionTitle = styled(Typography)(() => ({
  padding: '0 8px',
  marginTop: '16px',
  marginBottom: 0
}));

export const SectionTable = styled(Table)(() => ({
  width: '100%',
  height: 'auto',
  tableLayout: 'fixed'
}));
