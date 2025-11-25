import React from 'react';
import { NumberFormatBase, NumberFormatBaseProps, NumberFormatValues, useNumericFormat } from 'react-number-format';

interface FormattedIntegerNegativeAllowedNumericInputProps {
  onChange: (event: { target: { name: string; value: string | undefined } }) => void;
  name: string;
}

export const FormattedIntegerNegativeAllowedNumericInput = React.forwardRef<
  HTMLInputElement,
  NumberFormatBaseProps & FormattedIntegerNegativeAllowedNumericInputProps
>((props, ref) => {
  const { onChange, ...otherProps } = props;
  const { format, ...numericFormatterParams } = useNumericFormat({
    thousandSeparator: false,
    decimalScale: 0,
    allowNegative: true,
    fixedDecimalScale: true
  });

  const handleValueChange = (values: NumberFormatValues) => {
    onChange({
      target: {
        name: props.name,
        value: values.value
      }
    });
  };

  return (
    <NumberFormatBase
      {...numericFormatterParams}
      {...otherProps}
      getInputRef={ref}
      valueIsNumericString
      onValueChange={handleValueChange}
      format={format}
    />
  );
});

FormattedIntegerNegativeAllowedNumericInput.displayName = 'FormattedIntegerNegativeAllowedNumericInput';

export default FormattedIntegerNegativeAllowedNumericInput;
