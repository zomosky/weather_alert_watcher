import { DashboardResponse, LocationPayload } from "../types";

export async function fetchDashboard(payload: LocationPayload, signal?: AbortSignal): Promise<DashboardResponse> {
  const response = await fetch("/api/v1/dashboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`看板请求失败（${response.status}），请稍后重试。`);
  }

  return response.json() as Promise<DashboardResponse>;
}
