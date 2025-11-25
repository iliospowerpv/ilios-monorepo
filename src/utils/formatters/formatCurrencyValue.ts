export const formatCurrencyValue = (value: number) => {
  const formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    style: 'currency',
    currency: 'USD'
  });
  return formatter.format(value);
};

export default formatCurrencyValue;
