import React from 'react';
import { NumberFormatBase, NumberFormatBaseProps, NumberFormatValues, useNumericFormat } from 'react-number-format';

interface FormattedIntegerNumericInputProps {
  onChange: (event: { target: { name: string; value: string | undefined } }) => void;
  name: string;
}

export const FormattedIntegerNumericInput = React.forwardRef<
  HTMLInputElement,
  NumberFormatBaseProps & FormattedIntegerNumericInputProps
>((props, ref) => {
  const { onChange, ...otherProps } = props;
  const { format, ...numericFormatterParams } = useNumericFormat({
    thousandSeparator: false,
    decimalScale: 0,
    allowNegative: false,
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

FormattedIntegerNumericInput.displayName = 'FormattedIntegerNumericInput';

export default FormattedIntegerNumericInput;
