import * as React from 'react';
import ChevronRight from '@mui/icons-material/ChevronRight';
import ExpoandMore from '@mui/icons-material/ExpandMore';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Collapse from '@mui/material/Collapse';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';

import type { CompanySite } from '../../../../api';

const MENU_ITEM_HEIGHT = 48;

const ManuItemContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'flex-start',
  alignItems: 'center',
  position: 'relative',
  textDecoration: 'none',
  minHeight: MENU_ITEM_HEIGHT,
  maxHeight: MENU_ITEM_HEIGHT,
  paddingRight: 6,
  paddingTop: 6,
  paddingBottom: 6,
  boxSizing: 'border-box',
  whiteSpace: 'nowrap',
  color: theme.palette.primary.main
}));

interface MultiselectMenuItemBaseCommonProps {
  text: string;
  checked: boolean;
  onCheckedChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

type MultiselectMenuItemBaseProps =
  | (MultiselectMenuItemBaseCommonProps & {
      nested: true;
      indeterminate?: boolean;
      open?: boolean;
      handleOpenToggle?: () => void;
    })
  | (MultiselectMenuItemBaseCommonProps & {
      nested?: false | undefined;
      indeterminate: boolean;
      open: boolean;
      handleOpenToggle: () => void;
    });

const MultiselectMenuItemBase: React.FC<MultiselectMenuItemBaseProps> = ({
  text,
  checked,
  indeterminate,
  onCheckedChange,
  nested,
  handleOpenToggle,
  open
}) => (
  <ManuItemContainer component="li" sx={{ paddingLeft: nested ? '80px' : '6px' }}>
    {!nested ? (
      <IconButton sx={{ mx: '4px' }} color="inherit" size="small" edge="end" onClick={handleOpenToggle}>
        {open ? <ExpoandMore /> : <ChevronRight />}
      </IconButton>
    ) : null}
    <Checkbox checked={checked} indeterminate={indeterminate} onChange={onCheckedChange} />
    <ListItemText>
      <Typography noWrap>{text}</Typography>
    </ListItemText>
  </ManuItemContainer>
);

interface MenuItemWithNestedOptionsProps {
  id: number;
  name: string;
  options: CompanySite[];
  selectedList: number[];
  handleCheckedChange: (level: 'company' | 'site', companyId: number, siteId: number) => (checked: boolean) => void;
}

export const MenuItemWithNestedOptions: React.FC<MenuItemWithNestedOptionsProps> = ({
  name,
  id,
  options,
  selectedList,
  handleCheckedChange
}) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  const indeterminate = React.useMemo(
    () => options.some(({ id }) => selectedList.includes(id)),
    [options, selectedList]
  );
  const categorySelected = React.useMemo(
    () => (indeterminate ? options.every(({ id }) => selectedList.includes(id)) : false),
    [options, selectedList, indeterminate]
  );

  return (
    <>
      <MultiselectMenuItemBase
        key={id}
        text={name}
        checked={categorySelected}
        onCheckedChange={e => {
          const checked = e.target?.checked;
          handleCheckedChange('company', id, 0)(checked);
        }}
        open={isExpanded}
        indeterminate={indeterminate && !categorySelected}
        handleOpenToggle={() => setIsExpanded(prevOpen => !prevOpen)}
      />
      <Collapse in={isExpanded} timeout="auto" unmountOnExit>
        {options.map(option => (
          <MultiselectMenuItemBase
            key={option.id}
            nested
            text={option.name}
            checked={selectedList.includes(option.id)}
            onCheckedChange={e => {
              const checked = e.target?.checked;
              handleCheckedChange('site', id, option.id)(checked);
            }}
          />
        ))}
      </Collapse>
    </>
  );
};
