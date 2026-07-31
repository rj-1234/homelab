export interface Stem {
  species: string;
  note?: string;
}

export type GiftStatus = "not_opened" | "live" | "expired";

export interface Gift {
  id: string;
  stems: Stem[];
  message: string;
  sender: string;
  lifetime_ms: number;
  created_at: string;
  opened_at: string | null;
  expires_at: string | null;
  status: GiftStatus;
}

export async function fetchGifts(): Promise<Gift[]> {
  const res = await fetch("/api/admin/gifts");
  if (!res.ok) throw new Error(`Failed to load gifts (${res.status})`);
  return res.json();
}

export async function deleteGift(id: string): Promise<void> {
  const res = await fetch(`/api/admin/gifts/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete gift (${res.status})`);
}
