export const IST_TIME_ZONE = 'Asia/Kolkata';

type DateLike = Date | string | number | null | undefined;

function toDate(value: DateLike) {
  if (value === null || value === undefined || value === '') return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatIstTime(value: DateLike) {
  const date = toDate(value);
  if (!date) return '--:--:--';
  return date.toLocaleTimeString('en-IN', {
    timeZone: IST_TIME_ZONE,
    hour12: false,
  });
}

export function formatIstDateTime(value: DateLike) {
  const date = toDate(value);
  if (!date) return '-';
  return date.toLocaleString('en-IN', {
    timeZone: IST_TIME_ZONE,
    hour12: false,
  });
}

export function pctFromRiskValue(value: number | null | undefined) {
  const absolute = Math.abs(value ?? 0);
  return absolute <= 1 ? absolute * 100 : absolute;
}
