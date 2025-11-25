import { round } from 'lodash';

export const formatFloatValue = (value: number, noRounding?: boolean) => {
  const rounded = noRounding ? value : round(value, 2);
  const formatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return formatter.format(rounded);
};

export default formatFloatValue;
