export const formatPercentageValue = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return '';

  return `${value}%`;
};

export default formatPercentageValue;
