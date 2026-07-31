// Maps a Presidio entity_class to a vault shelf group + display order. Keeps the
// shelf organised the way the user thinks (Identity, Financial, …) rather than by
// raw recognizer name.

export interface FieldLike {
  entity_class: string;
}

export interface FieldGroup {
  title: string;
  fields: FieldLike[];
}

export const GROUPS = [
  {
    key: "identity",
    title: "Identity",
    classes: ["US_PASSPORT", "PASSPORT_MRZ", "US_SSN", "US_DRIVER_LICENSE", "ALIEN_NUMBER"],
  },
  { key: "financial", title: "Financial", classes: ["CREDIT_CARD", "US_BANK_NUMBER", "EIN"] },
  { key: "insurance", title: "Insurance", classes: ["INSURANCE_ID"] },
  { key: "immigration", title: "Immigration", classes: ["USCIS_RECEIPT", "SEVIS_ID", "I94_NUMBER"] },
  { key: "travel", title: "Travel", classes: ["TRAVEL_PNR"] },
  { key: "contact", title: "Contact", classes: ["PHONE_NUMBER", "EMAIL_ADDRESS"] },
] as const;

const CLASS_GROUP = new Map<string, string>(GROUPS.flatMap((g) => g.classes.map((c) => [c, g.key])));

export function groupOf(entityClass: string): string {
  return CLASS_GROUP.get(entityClass) ?? "other";
}

// Split a flat field list into ordered groups; empty groups are dropped.
export function intoGroups<T extends FieldLike>(fields: T[]): { title: string; fields: T[] }[] {
  const byKey = new Map<string, T[]>();
  for (const f of fields) {
    const key = groupOf(f.entity_class);
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key)!.push(f);
  }
  const out: { title: string; fields: T[] }[] = GROUPS.filter((g) => byKey.has(g.key)).map((g) => ({
    title: g.title as string,
    fields: byKey.get(g.key)!,
  }));
  if (byKey.has("other")) out.push({ title: "Other", fields: byKey.get("other")! });
  return out;
}
