import React from 'react';
import Autocomplete, { AutocompleteProps } from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import { SxProps, Theme } from '@mui/material/styles';

export interface SearchableSelectOption {
  label: string;
  value: string | number;
  disabled?: boolean;
}

type BaseAutocompleteProps = Omit<
  AutocompleteProps<SearchableSelectOption, false, boolean, false>,
  'renderInput' | 'options' | 'onChange' | 'value' | 'getOptionLabel' | 'isOptionEqualToValue'
>;

export interface SearchableSelectProps extends BaseAutocompleteProps {
  options: SearchableSelectOption[];
  value: string | number | null | undefined;
  onChange: (value: string | number | '') => void;
  label?: string;
  error?: boolean;
  helperText?: React.ReactNode;
  required?: boolean;
  variant?: 'filled' | 'outlined' | 'standard';
  size?: 'small' | 'medium';
  placeholder?: string;
  loading?: boolean;
  onBlur?: () => void;
  inputRef?: React.Ref<HTMLInputElement>;
  formControlSx?: SxProps<Theme>;
}

export const SearchableSelect: React.FC<SearchableSelectProps> = ({
  options,
  value,
  onChange,
  label,
  error,
  helperText,
  required,
  variant = 'outlined',
  size,
  placeholder,
  loading = false,
  onBlur,
  inputRef,
  formControlSx,
  disabled,
  fullWidth = true,
  sx,
  ...autocompleteProps
}) => {
  const selectedOption = options.find(opt => opt.value === value) ?? null;

  return (
    <Autocomplete
      {...autocompleteProps}
      options={options}
      value={selectedOption}
      onChange={(_event, newValue) => {
        onChange(newValue ? newValue.value : '');
      }}
      getOptionLabel={option => option.label}
      isOptionEqualToValue={(option, val) => option.value === val.value}
      getOptionDisabled={option => !!option.disabled}
      disabled={disabled}
      loading={loading}
      fullWidth={fullWidth}
      sx={sx}
      renderInput={params => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          required={required}
          error={error}
          helperText={helperText}
          variant={variant}
          size={size}
          inputRef={inputRef}
          onBlur={onBlur}
          sx={formControlSx}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading ? <CircularProgress color="inherit" size={20} /> : null}
                {params.InputProps.endAdornment}
              </>
            )
          }}
        />
      )}
    />
  );
};

export default SearchableSelect;
