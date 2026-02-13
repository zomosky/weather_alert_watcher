import { DashboardResponse, LocationPayload } from "../types";

export async function fetchDashboard(payload: LocationPayload): Promise<DashboardResponse> {
  const response = await fetch("/api/v1/dashboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Dashboard request failed: ${response.status}`);
  }

  return response.json() as Promise<DashboardResponse>;
}
