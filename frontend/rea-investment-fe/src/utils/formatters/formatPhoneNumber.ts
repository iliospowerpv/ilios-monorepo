export const normalizePhone = (value: string): string => {
  const digits = value.replace(/\D/g, '');
  if (digits.startsWith('1') && digits.length === 11) return digits.slice(1);
  return digits;
};

export const formatPhoneNumber = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return '';

  const raw = typeof value === 'number' ? Number(value).toFixed(0) : value;
  const digits = normalizePhone(raw);

  if (digits.length !== 10) return raw;

  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
};

export default formatPhoneNumber;
