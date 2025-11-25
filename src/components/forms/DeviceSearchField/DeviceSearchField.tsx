import React from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { debounce } from 'lodash';
import { AxiosError } from 'axios';

import TextField from '@mui/material/TextField';
import Autocomplete, { AutocompleteRenderInputParams, AutocompleteChangeReason } from '@mui/material/Autocomplete';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';

type SiteDevice = Awaited<ReturnType<typeof ApiClient.taskManagement.siteDevice>>['items'][number];

type AutocompleteProps = React.ComponentProps<typeof Autocomplete<SiteDevice>>;

type DeviceSearchFieldBaseProps = Pick<AutocompleteProps, 'ref' | 'onChange' | 'value' | 'onBlur' | 'disabled'>;

interface DeviceSearchFieldProps extends DeviceSearchFieldBaseProps {
  inputStyleOverrides?: AutocompleteProps['sx'];
  siteId: number;
}

type WithModifiers<T> = T & { modifiers?: 'hidden'[] };

const equalityCheckFn = (option: SiteDevice, selected: SiteDevice) => option.id === selected.id;
const generateLabelText = (option: SiteDevice) => `${option.name}`;

export const DeviceSearchField: React.ForwardRefExoticComponent<DeviceSearchFieldProps> = React.forwardRef(
  (props, ref) => {
    const { inputStyleOverrides, value, disabled, siteId, onChange } = props;
    const notify = useNotify();

    const [selectedValue, setSelectedValue] = React.useState<WithModifiers<SiteDevice> | null | undefined>(
      value ?? null
    );
    const [inputValue, setSetInputValue] = React.useState<string>(value ? generateLabelText(value) : '');
    const [searchTerm, setSearchTerm] = React.useState<string>(inputValue);

    const { data, isLoading, isFetching, error } = useQuery({
      queryKey: ['site-devices', { searchTerm, siteId }],
      queryFn: () => ApiClient.taskManagement.siteDevice(siteId, { search: searchTerm }),
      placeholderData: keepPreviousData,
      staleTime: 5 * 60 * 1000
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
      value: SiteDevice | null,
      reason: AutocompleteChangeReason
    ) => {
      setSelectedValue(value);
      onChange && onChange(event, value, reason);
    };

    const inputRenderer = (params: AutocompleteRenderInputParams) => (
      <TextField
        {...params}
        placeholder="Add Affected Device"
        error={!!error}
        helperText={error ? 'An error occurred while retrieving the devices list' : undefined}
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

    const excludeHiddenOptions = (options: WithModifiers<SiteDevice>[]) =>
      options.filter(option => !option.modifiers?.includes('hidden'));

    const options: WithModifiers<SiteDevice>[] = data ? [...data.items] : [];

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

DeviceSearchField.displayName = 'DeviceSearchField';

export default DeviceSearchField;
