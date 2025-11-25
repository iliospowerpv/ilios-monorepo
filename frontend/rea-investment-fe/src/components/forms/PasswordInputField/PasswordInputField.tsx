import React from 'react';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import Visibility from '@mui/icons-material/Visibility';
import TextField from '@mui/material/TextField';

import type { FilledTextFieldProps } from '@mui/material/TextField';

const passwordFieldStyles = {
  mt: 2,
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

const PasswordInputField = React.forwardRef<HTMLInputElement, FilledTextFieldProps>((props, ref) => {
  const { onChange, onBlur, onFocus, helperText, error, ...forwardProps } = props;

  const [isPasswordHidden, setIsPasswordHidden] = React.useState(true);
  const [isFocused, setIsFocused] = React.useState(false);
  const [observedValue, setObservedValue] = React.useState('');

  React.useEffect(() => {
    if (!isFocused && !observedValue) setIsPasswordHidden(true);
  }, [isFocused, observedValue]);

  const toggleShowPassword = () => setIsPasswordHidden(hidden => !hidden);

  const handleMouseDownPassword = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
  };

  const handleFocus: React.FocusEventHandler<HTMLInputElement | HTMLTextAreaElement> = e => {
    setIsFocused(true);
    onFocus && onFocus(e);
  };

  const handleBlur: React.FocusEventHandler<HTMLInputElement | HTMLTextAreaElement> = e => {
    setIsFocused(false);
    onBlur && onBlur(e);
  };

  const handleChange: React.ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = e => {
    setObservedValue(e.target.value);
    onChange && onChange(e);
  };

  const showPasswordVisibilityToggleBtn = isFocused || !!observedValue;
  const helperTextToShow = error || isFocused ? helperText : '';

  return (
    <TextField
      {...forwardProps}
      ref={ref}
      autoComplete="off"
      fullWidth
      type={isPasswordHidden ? 'password' : 'text'}
      helperText={helperTextToShow}
      error={error}
      sx={passwordFieldStyles}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onChange={handleChange}
      InputProps={
        showPasswordVisibilityToggleBtn
          ? {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label="toggle password visibility"
                    onClick={toggleShowPassword}
                    onMouseDown={handleMouseDownPassword}
                    edge="end"
                  >
                    {isPasswordHidden ? <Visibility /> : <VisibilityOff />}
                  </IconButton>
                </InputAdornment>
              )
            }
          : undefined
      }
    />
  );
});

PasswordInputField.displayName = 'PasswordInputField';

export { PasswordInputField };
