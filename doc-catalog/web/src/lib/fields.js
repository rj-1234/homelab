// Maps a Presidio entity_class to a vault shelf group + display order. Keeps the
// shelf organised the way the user thinks (Identity, Financial, …) rather than by
// raw recognizer name.

export const GROUPS = [
  { key: 'identity', title: 'Identity',
    classes: ['US_PASSPORT', 'PASSPORT_MRZ', 'US_SSN', 'US_DRIVER_LICENSE', 'ALIEN_NUMBER'] },
  { key: 'financial', title: 'Financial',
    classes: ['CREDIT_CARD', 'US_BANK_NUMBER', 'EIN'] },
  { key: 'insurance', title: 'Insurance',
    classes: ['INSURANCE_ID'] },
  { key: 'immigration', title: 'Immigration',
    classes: ['USCIS_RECEIPT', 'SEVIS_ID', 'I94_NUMBER'] },
  { key: 'travel', title: 'Travel',
    classes: ['TRAVEL_PNR'] },
  { key: 'contact', title: 'Contact',
    classes: ['PHONE_NUMBER', 'EMAIL_ADDRESS'] }
];

const CLASS_GROUP = new Map(
  GROUPS.flatMap((g) => g.classes.map((c) => [c, g.key]))
);

export function groupOf(entityClass) {
  return CLASS_GROUP.get(entityClass) ?? 'other';
}

// Split a flat field list into ordered groups; empty groups are dropped.
export function intoGroups(fields) {
  const byKey = new Map();
  for (const f of fields) {
    const key = groupOf(f.entity_class);
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(f);
  }
  const out = GROUPS
    .filter((g) => byKey.has(g.key))
    .map((g) => ({ title: g.title, fields: byKey.get(g.key) }));
  if (byKey.has('other')) out.push({ title: 'Other', fields: byKey.get('other') });
  return out;
}
