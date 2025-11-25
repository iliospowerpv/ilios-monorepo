export const formatPhoneNumber = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return '';

  const phoneNumberString = typeof value === 'number' ? Number(value).toFixed(0) : value;
  let formattedStr = '';

  for (let i = 0; i < phoneNumberString.length; i++) {
    const remainder = phoneNumberString.length - i;

    if (i !== 0 && i % 3 === 0 && remainder >= 3) formattedStr += '.';

    formattedStr += phoneNumberString.charAt(i);
  }

  return formattedStr;
};

export default formatPhoneNumber;
