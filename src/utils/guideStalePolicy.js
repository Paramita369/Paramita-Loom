const MACAU_TIME_ZONE = 'Asia/Macau';

export const GUIDE_STALE_POLICY_CODE = 'remove_from_primary_entry_when_overdue';

export const GUIDE_STALE_POLICY_TEXT =
  '如超過下次覆核日仍未更新，會先退出首頁與指南入口，待完成覆核後再重新列入。';

function toMacauDateString(referenceDate = new Date()) {
  const date = referenceDate instanceof Date ? referenceDate : new Date(referenceDate);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError(`invalid reference date: ${referenceDate}`);
  }

  return new Intl.DateTimeFormat('en-CA', {
    timeZone: MACAU_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

function normalizeDateOnly(value) {
  return typeof value === 'string' ? value.trim().slice(0, 10) : '';
}

export function isGuideOverdue(nextReviewAt, referenceDate = new Date()) {
  const reviewDate = normalizeDateOnly(nextReviewAt);

  if (!reviewDate) {
    return false;
  }

  return toMacauDateString(referenceDate) > reviewDate;
}

export function filterVisibleGuides(entries, referenceDate = new Date()) {
  return entries.filter((entry) => !isGuideOverdue(entry.nextReviewAt, referenceDate));
}
