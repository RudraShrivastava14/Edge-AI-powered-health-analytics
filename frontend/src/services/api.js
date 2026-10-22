import { idToken } from "./auth.js";

let base = "";
export function initApi(cfg) { base = cfg.apiEndpoint.replace(/\/$/, ""); }

async function call(path, opts = {}) {
  const token = await idToken();
  const res = await fetch(base + path, {
    ...opts,
    headers: { "content-type": "application/json", ...(token ? { authorization: token } : {}), ...(opts.headers || {}) },
  });
  if (res.status === 401) throw Object.assign(new Error("Session expired"), { status: 401 });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(body.detail || res.statusText), { status: res.status });
  return body;
}

export const api = {
  devices: () => call("/v1/devices"),
  latest: (id) => call(`/v1/devices/${encodeURIComponent(id)}/vitals/latest`),
  vitals: (id, from, to, cursor) =>
    call(`/v1/devices/${encodeURIComponent(id)}/vitals?from=${from}&to=${to}&limit=1000${cursor ? `&cursor=${cursor}` : ""}`),
  allVitals: async (id, from, to) => {
    let items = [], cursor = null, pages = 0;
    do {
      const r = await api.vitals(id, from, to, cursor);
      items = items.concat(r.items);
      cursor = r.nextCursor;
    } while (cursor && ++pages < 10);
    return items;
  },
  stats: (id, hours = 24) => call(`/v1/devices/${encodeURIComponent(id)}/stats?hours=${hours}`),
  alerts: (status = "all", deviceId) =>
    call(`/v1/alerts?status=${status}&limit=100${deviceId ? `&deviceId=${encodeURIComponent(deviceId)}` : ""}`),
  ack: (alertId, note) => call(`/v1/alerts/${encodeURIComponent(alertId)}/ack`, { method: "POST", body: JSON.stringify({ note }) }),
};
