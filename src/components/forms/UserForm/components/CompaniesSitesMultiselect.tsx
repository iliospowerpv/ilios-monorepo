import * as React from 'react';
import Select from '@mui/material/Select';
import FormControl from '@mui/material/FormControl';
import FormHelperText from '@mui/material/FormHelperText';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import HourglassBottomRoundedIcon from '@mui/icons-material/HourglassBottomRounded';
import { MenuItemWithNestedOptions } from './MenuItemWithNestedOptions';
import { SelectedItemsDisplayRenderer } from './SelectedItemsDisplayRenderer';

import type { FieldError, Merge } from 'react-hook-form';
import type { CompanySites } from '../../../../api';

const MENU_ITEM_HEIGHT = 48;

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

const menuPaperProps = {
  style: {
    maxHeight: MENU_ITEM_HEIGHT * 4.5 + 8
  }
};

interface CompaniesSitesMultiselectProps {
  data: CompanySites[];
  optionsLoading: boolean;
  disabled?: boolean;
  loadingError?: Error | null;
  validationError?: Merge<FieldError, (FieldError | undefined)[]> | undefined;
  onBlur?: () => void;
  value: number[];
  onChange: (siteIds: number[]) => void;
}

export const CompaniesSitesMultiselect: React.FC<CompaniesSitesMultiselectProps> = ({
  data,
  optionsLoading,
  loadingError,
  validationError,
  disabled,
  value: selectedSiteIds,
  onBlur,
  onChange
}) => {
  const [dropDownopen, setDropdownOpen] = React.useState<boolean>(false);
  const inputRef = React.useRef<{ focus: () => void }>(null);
  const [selectDisplayFocused, setSelectDisplayFocused] = React.useState<boolean>(false);

  const hasSelectedItems = selectedSiteIds.length > 0;
  const selectedCompanySites = React.useMemo<CompanySites[]>(() => {
    if (!hasSelectedItems) return [];
    return data
      .map(company => ({
        ...company,
        sites: company.sites.filter(site => selectedSiteIds.includes(site.id))
      }))
      .filter(company => company.sites.length > 0);
  }, [data, hasSelectedItems, selectedSiteIds]);

  const selectedInGroupIds: Record<number, number[]> = React.useMemo(
    () =>
      selectedCompanySites.reduce(
        (record, company) => ({ ...record, [company.id]: company.sites.map(site => site.id) }),
        {}
      ),
    [selectedCompanySites]
  );

  const handleOpen: () => void = () => {
    setDropdownOpen(true);
  };

  const handleClose: () => void = () => {
    setDropdownOpen(false);
    setSelectDisplayFocused(false);
  };

  const handleSelectDisplayFocus = () => {
    setSelectDisplayFocused(true);
  };

  const handleSelectDisplayBlur = () => {
    setSelectDisplayFocused(false);
    onBlur && !dropDownopen && onBlur();
  };

  const handleSelectDisplayMouseDown: React.MouseEventHandler<HTMLDivElement> = e => {
    if (e.button === 0 || e.button === 2) {
      e.preventDefault();

      if (
        e.target instanceof Element &&
        selectDisplayFocused &&
        (e.target.classList.contains('MuiChip-deleteIcon') ||
          e.target.classList.contains('MuiChip-label') ||
          e.target.tagName === 'path')
      ) {
        e.stopPropagation();
        return;
      }

      if (!selectDisplayFocused && !dropDownopen) {
        inputRef.current?.focus();
        return;
      } else if (selectDisplayFocused) {
        setDropdownOpen(true);
        return;
      }
    }
  };

  const handleSelectedChange: (
    level: 'company' | 'site',
    companyId: number,
    siteId: number
  ) => (checked: boolean) => void = (level, companyId, siteId) => {
    if (level === 'company') {
      const companySitesIds = data.find(company => company.id === companyId)?.sites.map(site => site.id) ?? [];

      return checked => {
        onChange(
          checked
            ? [...selectedSiteIds, ...companySitesIds.filter(id => !selectedSiteIds.includes(id))]
            : selectedSiteIds.filter(id => !companySitesIds.includes(id))
        );
      };
    } else {
      return checked => {
        onChange(
          checked
            ? selectedSiteIds.includes(siteId)
              ? selectedSiteIds
              : [...selectedSiteIds, siteId]
            : selectedSiteIds.filter(id => id !== siteId)
        );
      };
    }
  };

  const handleSiteUnselect: (companyId: number, siteId: number) => void = (companyId: number, siteId: number) => {
    handleSelectedChange('site', companyId, siteId)(false);
  };

  return (
    <>
      <FormControl variant="filled" error={!!loadingError || !!validationError} required sx={noBottomLineStyles}>
        <InputLabel
          error={!!loadingError || !!validationError}
          className={selectDisplayFocused || dropDownopen ? 'Mui-focused' : undefined}
        >
          Project Access
        </InputLabel>
        <Select
          displayEmpty
          value={selectDisplayFocused || hasSelectedItems || dropDownopen ? 'stub' : ''}
          inputRef={inputRef}
          open={dropDownopen}
          onOpen={handleOpen}
          onClose={handleClose}
          disabled={optionsLoading || !!loadingError || disabled}
          error={!!loadingError || !!validationError}
          MenuProps={{ PaperProps: menuPaperProps }}
          IconComponent={optionsLoading ? HourglassBottomRoundedIcon : undefined}
          SelectDisplayProps={{
            onMouseDown: handleSelectDisplayMouseDown,
            onBlur: handleSelectDisplayBlur,
            onFocus: handleSelectDisplayFocus
          }}
          renderValue={() => (
            <SelectedItemsDisplayRenderer
              dropdownOpen={dropDownopen}
              displayFocused={selectDisplayFocused}
              selectedCompaniesSites={selectedCompanySites}
              handleSiteUnselect={handleSiteUnselect}
            />
          )}
        >
          <MenuItem value="stub" sx={{ display: 'none' }} />
          {data.map(({ id, name, sites }) => {
            return (
              <MenuItemWithNestedOptions
                key={id}
                id={id}
                name={name}
                options={sites}
                selectedList={selectedInGroupIds[id] || []}
                handleCheckedChange={handleSelectedChange}
              />
            );
          })}
        </Select>
        {(loadingError || validationError) && (
          <FormHelperText error>{loadingError?.message || validationError?.message}</FormHelperText>
        )}
      </FormControl>
    </>
  );
};
