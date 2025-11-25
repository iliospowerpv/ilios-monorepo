import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@mui/material';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import { debounce } from 'lodash';

import { SearchField, SearchBarItem, SearchAndActionsContainer } from './SearchAndActions.styles';
import SettingsIcon from '@mui/icons-material/Settings';

interface SearchAndActionsProps {
  showSearch?: boolean;
  showFilter?: boolean;
  showExport?: boolean;
  showAdd?: boolean;
  showColumns?: boolean;
  reversOrder?: boolean;
  searchPlaceholder?: string;
  btnAddLabel?: string;
  onSearch?: (value: string) => void;
  onAdd?: () => void;
  onFilter?: () => void;
  onExport?: () => void;
  onColumns?: () => void;
  customActions?: React.ReactElement;
}

const SearchAndActions: React.FC<SearchAndActionsProps> = ({
  onSearch,
  onFilter,
  onAdd,
  onExport,
  onColumns,
  showSearch,
  showFilter,
  showExport,
  showAdd,
  showColumns,
  reversOrder,
  searchPlaceholder,
  btnAddLabel,
  customActions
}) => {
  const searchLabel = searchPlaceholder || 'Search';
  const addLabel = btnAddLabel || 'Add';
  const [inputValue, setInputValue] = useState<string>('');

  const debouncedSearch = useCallback(
    debounce(searchTerm => {
      onSearch && onSearch(searchTerm);
    }, 400),
    []
  );

  useEffect(() => {
    if (inputValue.length >= 3) {
      debouncedSearch(inputValue);
    } else {
      debouncedSearch('');
    }
  }, [inputValue, debouncedSearch]);

  const FiltersContent = (
    <>
      {showFilter && (
        <Button variant="outlined" data-testid="actions__filters-btn" onClick={onFilter} startIcon={<FilterAltIcon />}>
          Filters
        </Button>
      )}
      {showColumns && (
        <Button variant="outlined" data-testid="actions__columns-btn" onClick={onColumns} startIcon={<SettingsIcon />}>
          Set Columns
        </Button>
      )}
    </>
  );

  const SearchContent = (
    <>
      {showSearch && (
        <SearchField
          hiddenLabel
          id="search-field"
          data-testid="actions__search-field"
          type="search"
          size="small"
          variant="filled"
          placeholder={searchLabel}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <SearchIcon />
              </InputAdornment>
            )
          }}
        />
      )}
    </>
  );

  const ActionsContent = (
    <>
      {showExport && (
        <Button variant="outlined" color="primary" data-testid="actions__export-btn" onClick={onExport}>
          Export as
        </Button>
      )}
      {showAdd && (
        <Button variant="contained" color="primary" data-testid="actions__add-btn" onClick={onAdd}>
          {addLabel}
        </Button>
      )}
    </>
  );

  return (
    <SearchAndActionsContainer data-testid="actions__container">
      {reversOrder ? (
        <>
          <SearchBarItem>
            {customActions}
            {FiltersContent}
          </SearchBarItem>
          <SearchBarItem>
            {SearchContent}
            {ActionsContent}
          </SearchBarItem>
        </>
      ) : (
        <>
          <SearchBarItem>
            {customActions}
            {SearchContent}
          </SearchBarItem>
          <SearchBarItem>
            {FiltersContent}
            {ActionsContent}
          </SearchBarItem>
        </>
      )}
    </SearchAndActionsContainer>
  );
};

export default SearchAndActions;
