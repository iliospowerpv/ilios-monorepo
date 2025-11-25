import React, { useEffect } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { debounce } from 'lodash';
import { AxiosError } from 'axios';

import TextField from '@mui/material/TextField';
import Autocomplete, { AutocompleteRenderInputParams, AutocompleteChangeReason } from '@mui/material/Autocomplete';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';

type SiteUser = Awaited<ReturnType<typeof ApiClient.reports.getSiteList>>['items'][number];

type AutocompleteProps = React.ComponentProps<typeof Autocomplete<SiteUser>>;

type AssigneeSearchFieldBaseProps = Pick<AutocompleteProps, 'ref' | 'onChange' | 'value' | 'onBlur' | 'disabled'>;

interface AssigneeSearchFieldProps extends AssigneeSearchFieldBaseProps {
  inputStyleOverrides?: AutocompleteProps['sx'];
  placeholder?: string;
  company: string;
}

type WithModifiers<T> = T & { modifiers?: 'hidden'[] };

const equalityCheckFn = (option: SiteUser, selected: SiteUser) => option.id === selected.id;
const generateLabelText = (option: SiteUser) => `${option.name}`;

export const SiteSearchField: React.ForwardRefExoticComponent<AssigneeSearchFieldProps> = React.forwardRef(
  (props, ref) => {
    const { inputStyleOverrides, value, disabled, onChange, placeholder, company } = props;
    const notify = useNotify();

    const [selectedValue, setSelectedValue] = React.useState<WithModifiers<SiteUser> | null | undefined>(value ?? null);
    const [inputValue, setSetInputValue] = React.useState<string>(value ? generateLabelText(value) : '');
    const [searchTerm, setSearchTerm] = React.useState<string>(inputValue);

    useEffect(() => {
      if (!company || company) {
        setSelectedValue(null);
      }
    }, [company]);

    const { data, isLoading, isFetching, error } = useQuery({
      queryKey: ['reports-site', { searchTerm, company }],
      queryFn: () => ApiClient.reports.getSiteList(company, searchTerm),
      placeholderData: keepPreviousData,
      staleTime: 5 * 60 * 1000,
      refetchInterval: 5 * 60 * 1000,
      enabled: !!company
    });

    React.useEffect(() => {
      if (error && error instanceof AxiosError) notify(error.response?.data?.detail);
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
        placeholder={placeholder || 'Site'}
        error={!!error}
        helperText={error ? 'An error occurred while retrieving the site list' : undefined}
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

SiteSearchField.displayName = 'SiteSearchField';

export default SiteSearchField;
