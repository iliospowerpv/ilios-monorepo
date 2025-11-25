import React from 'react';
import { NumberFormatBase, NumberFormatBaseProps, NumberFormatValues, useNumericFormat } from 'react-number-format';

interface FormattedNumericInputProps {
  onChange: (event: { target: { name: string; value: string | undefined } }) => void;
  name: string;
}

export const FormattedNumericInputWithMinus = React.forwardRef<
  HTMLInputElement,
  NumberFormatBaseProps & FormattedNumericInputProps
>((props, ref) => {
  const { onChange, ...otherProps } = props;
  const { format, ...numericFormatterParams } = useNumericFormat({
    thousandSeparator: true,
    decimalScale: 2,
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

FormattedNumericInputWithMinus.displayName = 'FormattedNumericInputWithMinus';

export default FormattedNumericInputWithMinus;
