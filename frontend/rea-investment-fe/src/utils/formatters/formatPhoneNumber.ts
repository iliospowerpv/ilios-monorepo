export const formatPhoneNumber = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return '';

  const raw = typeof value === 'number' ? Number(value).toFixed(0) : value;
  const digits = raw.replace(/\D/g, '').replace(/^1(\d{10})$/, '$1');

  if (digits.length !== 10) return raw;

  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
};

export default formatPhoneNumber;
