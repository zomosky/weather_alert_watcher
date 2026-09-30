import { WarningItem } from "../types";

export function warningKey(warning: WarningItem): string {
  return `${warning.province}-${warning.hazard_type}-${warning.issue_time}-${warning.detail_url}`;
}
