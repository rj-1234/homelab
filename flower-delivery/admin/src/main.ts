import "./styles/organic.css";
import "./styles/app.css";
import { fetchGifts, type Gift, type GiftStatus } from "./api";

const app = document.getElementById("app")!;
const PUBLIC_BASE_URL = "https://flowers.ch33ky.org";

const STATUS_LABEL: Record<GiftStatus, string> = {
  not_opened: "not opened",
  live: "live",
  expired: "expired",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatLifetime(ms: number): string {
  const hours = ms / 3_600_000;
  if (hours % 24 === 0) {
    const days = hours / 24;
    return days === 1 ? "1 day" : `${days} days`;
  }
  return `${hours} hours`;
}

function speciesLabel(species: string): string {
  return species.charAt(0).toUpperCase() + species.slice(1);
}

function renderStems(gift: Gift): string {
  const names = gift.stems.map((s) => speciesLabel(s.species)).join(", ");
  const noteCount = gift.stems.filter((s) => s.note && s.note.trim()).length;
  const badge = noteCount > 0 ? `<span class="note-count" title="${noteCount} pinned note${noteCount === 1 ? "" : "s"}">${noteCount}</span>` : "";
  return `${escapeHtml(names)}${badge}`;
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function renderSkeleton(): string {
  const row = `<tr class="skeleton-row">${Array.from({ length: 9 })
    .map(() => `<td><div class="skeleton-bar"></div></td>`)
    .join("")}</tr>`;
  return row.repeat(6);
}

function renderEmpty(): string {
  return `
    <div class="empty-state">
      <h2>No bouquets sent yet</h2>
      <p>Once someone composes one at the public site, it'll show up here.</p>
    </div>`;
}

function renderError(message: string): string {
  return `
    <div class="error-state">
      <h2>Couldn't load gifts</h2>
      <p>${escapeHtml(message)}</p>
      <button type="button" class="btn btn-secondary" id="retry">Try again</button>
    </div>`;
}

function renderTable(gifts: Gift[]): string {
  const rows = gifts
    .map((g) => {
      const shareUrl = `${PUBLIC_BASE_URL}/g/${g.id}`;
      return `
        <tr>
          <td>${formatDate(g.created_at)}</td>
          <td><span class="status-badge status-${g.status}">${STATUS_LABEL[g.status]}</span></td>
          <td>${escapeHtml(g.sender || "—")}</td>
          <td class="message-cell" title="${escapeHtml(g.message)}">${escapeHtml(g.message)}</td>
          <td class="stems-cell">${renderStems(g)}</td>
          <td>${formatLifetime(g.lifetime_ms)}</td>
          <td>${formatDate(g.opened_at)}</td>
          <td>${formatDate(g.expires_at)}</td>
          <td class="id-cell">
            <div class="link-actions">
              <button type="button" class="btn btn-secondary btn-icon copy-link" data-url="${shareUrl}" title="Copy link">⧉</button>
              <a class="btn btn-ghost" href="${shareUrl}?dev=1" target="_blank" rel="noreferrer">Open</a>
            </div>
          </td>
        </tr>`;
    })
    .join("");

  return `
    <div class="table-wrap">
      <table class="gifts">
        <thead>
          <tr>
            <th>Sent</th>
            <th>Status</th>
            <th>From</th>
            <th>Message</th>
            <th>Stems</th>
            <th>Lifetime</th>
            <th>Opened</th>
            <th>Expires</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function wireCopyButtons() {
  app.querySelectorAll<HTMLButtonElement>(".copy-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      const url = btn.dataset.url!;
      navigator.clipboard.writeText(url).then(() => {
        const original = btn.textContent;
        btn.textContent = "✓";
        setTimeout(() => { btn.textContent = original; }, 1200);
      });
    });
  });
}

function renderHeader(count: number) {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Flowers — sent bouquets</h1>
        <div class="page-meta">${count} ${count === 1 ? "bouquet" : "bouquets"}</div>
      </div>
      <button type="button" class="btn btn-secondary" id="refresh">Refresh</button>
    </div>`;
}

async function load() {
  app.innerHTML = `
    <div class="page">
      ${renderHeader(0)}
      <div class="table-wrap">
        <table class="gifts">
          <tbody>${renderSkeleton()}</tbody>
        </table>
      </div>
    </div>`;

  try {
    const gifts = await fetchGifts();
    app.innerHTML = `
      <div class="page">
        ${renderHeader(gifts.length)}
        ${gifts.length === 0 ? renderEmpty() : renderTable(gifts)}
      </div>`;
    wireCopyButtons();
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    app.innerHTML = `
      <div class="page">
        ${renderHeader(0)}
        ${renderError(message)}
      </div>`;
    document.getElementById("retry")?.addEventListener("click", load);
  }

  document.getElementById("refresh")?.addEventListener("click", load);
}

load();
