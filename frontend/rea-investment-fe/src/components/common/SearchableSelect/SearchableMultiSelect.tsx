import React from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Checkbox from '@mui/material/Checkbox';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import { SxProps, Theme } from '@mui/material/styles';
import { SearchableSelectOption } from './SearchableSelect';

export interface SearchableMultiSelectProps {
  options: SearchableSelectOption[];
  value: (string | number)[];
  onChange: (values: (string | number)[]) => void;
  label?: string;
  error?: boolean;
  helperText?: React.ReactNode;
  required?: boolean;
  variant?: 'filled' | 'outlined' | 'standard';
  size?: 'small' | 'medium';
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
  onBlur?: () => void;
  inputRef?: React.Ref<HTMLInputElement>;
  formControlSx?: SxProps<Theme>;
  fullWidth?: boolean;
  sx?: SxProps<Theme>;
  disableCloseOnSelect?: boolean;
}

export const SearchableMultiSelect: React.FC<SearchableMultiSelectProps> = ({
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
  disabled,
  onBlur,
  inputRef,
  formControlSx,
  fullWidth = true,
  sx,
  disableCloseOnSelect = true
}) => {
  const selectedOptions = options.filter(opt => value.includes(opt.value));

  return (
    <Autocomplete
      multiple
      options={options}
      value={selectedOptions}
      onChange={(_event, newValue) => {
        onChange(newValue.map(opt => opt.value));
      }}
      getOptionLabel={option => option.label}
      isOptionEqualToValue={(option, val) => option.value === val.value}
      getOptionDisabled={option => !!option.disabled}
      disableCloseOnSelect={disableCloseOnSelect}
      disabled={disabled}
      loading={loading}
      fullWidth={fullWidth}
      sx={sx}
      renderOption={(props, option, { selected }) => (
        <li {...props}>
          <Checkbox checked={selected} sx={{ mr: 1 }} />
          {option.label}
        </li>
      )}
      renderTags={(tagValues, getTagProps) =>
        tagValues.map((option, index) => {
          const { key, ...chipProps } = getTagProps({ index });
          return <Chip key={key} label={option.label} {...chipProps} />;
        })
      }
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

export default SearchableMultiSelect;
