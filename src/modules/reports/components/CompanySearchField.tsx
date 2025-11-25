import React from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { debounce } from 'lodash';
import { AxiosError } from 'axios';

import TextField from '@mui/material/TextField';
import Autocomplete, { AutocompleteRenderInputParams, AutocompleteChangeReason } from '@mui/material/Autocomplete';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';

type SiteUser = Awaited<ReturnType<typeof ApiClient.reports.getCompanyList>>['items'][number];

type AutocompleteProps = React.ComponentProps<typeof Autocomplete<SiteUser>>;

type AssigneeSearchFieldBaseProps = Pick<AutocompleteProps, 'ref' | 'onChange' | 'value' | 'onBlur' | 'disabled'>;

interface AssigneeSearchFieldProps extends AssigneeSearchFieldBaseProps {
  inputStyleOverrides?: AutocompleteProps['sx'];
  placeholder?: string;
}

type WithModifiers<T> = T & { modifiers?: 'hidden'[] };

const equalityCheckFn = (option: SiteUser, selected: SiteUser) => option.id === selected.id;
const generateLabelText = (option: SiteUser) => `${option.name}`;

export const CompanySearchField: React.ForwardRefExoticComponent<AssigneeSearchFieldProps> = React.forwardRef(
  (props, ref) => {
    const { inputStyleOverrides, value, disabled, onChange, placeholder } = props;
    const notify = useNotify();

    const [selectedValue, setSelectedValue] = React.useState<WithModifiers<SiteUser> | null | undefined>(value ?? null);
    const [inputValue, setSetInputValue] = React.useState<string>(value ? generateLabelText(value) : '');
    const [searchTerm, setSearchTerm] = React.useState<string>(inputValue);

    const { data, isLoading, isFetching, error } = useQuery({
      queryKey: ['reports-company', { searchTerm }],
      queryFn: () => ApiClient.reports.getCompanyList(searchTerm),
      placeholderData: keepPreviousData,
      staleTime: 5 * 60 * 1000,
      refetchInterval: 5 * 60 * 1000
    });

    React.useEffect(() => {
      if (error && error instanceof AxiosError) notify(error.response?.data);
    }, [error, notify]);

    const updateSearchTerm = debounce((searchTerm: string) => setSearchTerm(searchTerm), 400);

    React.useEffect(() => {
      if (selectedValue && generateLabelText(selectedValue) === inputValue) {
        updateSearchTerm('');
        return;
      }
      updateSearchTerm(inputValue);
    }, [selectedValue, inputValue, updateSearchTerm]);

    const handleInputChange = (e: React.SyntheticEvent<Element, Event>, value: string) => setSetInputValue(value);

    const handleSelectedChange = (
      event: React.SyntheticEvent<Element, Event>,
      value: SiteUser | null,
      reason: AutocompleteChangeReason
    ) => {
      setSelectedValue(value);
      onChange && onChange(event, value, reason);
    };

    const inputRenderer = (params: AutocompleteRenderInputParams) => (
      <TextField
        {...params}
        placeholder={placeholder || 'Company'}
        error={!!error}
        helperText={error ? 'An error occurred while retrieving the companies list' : undefined}
        inputRef={ref}
        InputProps={{
          ...params.InputProps,
          sx: inputStyleOverrides,
          endAdornment: (
            <React.Fragment>
              {isLoading || isFetching ? <CircularProgress color="inherit" size={20} /> : undefined}
              {params.InputProps.endAdornment}
            </React.Fragment>
          )
        }}
      />
    );

    const excludeHiddenOptions = (options: WithModifiers<SiteUser>[]) =>
      options.filter(option => !option.modifiers?.includes('hidden'));

    const options: WithModifiers<SiteUser>[] = data && data.items ? [...data.items] : [];

    if (selectedValue && !options.find(option => option.id === selectedValue.id)) {
      options.unshift({ ...selectedValue, modifiers: ['hidden'] });
    }

    return (
      <Autocomplete
        value={selectedValue}
        onChange={handleSelectedChange}
        inputValue={inputValue}
        size="small"
        options={options}
        filterOptions={excludeHiddenOptions}
        loading={isLoading || isFetching}
        isOptionEqualToValue={equalityCheckFn}
        getOptionLabel={generateLabelText}
        getOptionKey={option => option.id}
        forcePopupIcon={true}
        clearOnBlur
        onInputChange={handleInputChange}
        renderInput={inputRenderer}
        disabled={disabled}
      />
    );
  }
);

CompanySearchField.displayName = 'CompanySearchField';

export default CompanySearchField;
