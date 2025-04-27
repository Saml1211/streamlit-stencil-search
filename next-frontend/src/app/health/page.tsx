"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useHealthStatus, useIntegrationStatus, ApiError, HealthStatus, IntegrationStatus, useTriggerCommand } from "@/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, AlertCircle, CheckCircle, Server, Power, PowerOff, Info, Filter, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose
} from "@/components/ui/dialog";
import { toast } from "sonner";

// Helper to render status badge
const StatusBadge = ({ status }: { status: string }) => {
  let variant: "default" | "secondary" | "destructive" | "outline" = "secondary";
  let Icon = AlertCircle;
  let text = status.charAt(0).toUpperCase() + status.slice(1);

  if (status === "ok" || status === "connected" || status === "running") {
    variant = "default"; // Use default (often green) for positive status
    Icon = CheckCircle;
    text = status === "connected" ? "Connected" : "OK";
  } else if (status === "error" || status === "disconnected") {
    variant = "destructive";
    Icon = status === "disconnected" ? PowerOff : AlertCircle;
    text = status === "disconnected" ? "Disconnected" : "Error";
  }

  return (
    <Badge variant={variant} className="flex items-center gap-1 w-fit">
       <Icon className="h-3 w-3" />
       <span>{text}</span>
    </Badge>
  );
};


export default function HealthPage() {
  const { data: health, isLoading: isLoadingHealth, isError: isErrorHealth, error: errorHealth } = useHealthStatus();
  const { data: integration, isLoading: isLoadingIntegration, isError: isErrorIntegration, error: errorIntegration } = useIntegrationStatus();
  const [healthDetail, setHealthDetail] = useState<any>(null);
  const [loadingHealthDetail, setLoadingHealthDetail] = useState(false);
  const [errorHealthDetail, setErrorHealthDetail] = useState<string | null>(null);

  const [exporting, setExporting] = useState(false);

  // Issue filter/sort UI state
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string>("severity");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Issue detail modal UI state
  const [selectedIssue, setSelectedIssue] = useState<any | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const triggerCommand = useTriggerCommand();

  // Fetch stencil health analytics
  useEffect(() => {
    setLoadingHealthDetail(true);
    setErrorHealthDetail(null);
    triggerCommand.mutateAsync({ command: "get_stencil_health" })
      .then(res => {
        if (res.status === "ok") setHealthDetail(res.result);
        else throw new Error(res.message || "Unknown error");
      })
      .catch(e => setErrorHealthDetail(e.message))
      .finally(() => setLoadingHealthDetail(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Loading/error handling for overall status
  const isLoading = isLoadingHealth || isLoadingIntegration || loadingHealthDetail;
  const isError = isErrorHealth || isErrorIntegration || !!errorHealthDetail;
  const error = errorHealth || errorIntegration || errorHealthDetail;

  // Issue table filter/sort
  type IssueType = {
    path: string;
    issue: string;
    severity: string;
    type: string;
    details?: string;
  };
  const issues: IssueType[] = (healthDetail?.issues || []) as IssueType[];

  const filteredIssues = useMemo(() => {
    let out = [...issues];
    if (severityFilter)
      out = out.filter((i) => i.severity === severityFilter);
    if (typeFilter)
      out = out.filter((i) => i.type === typeFilter);
    out.sort((a, b) => {
      if (sortKey === "severity") {
        const sev: Record<string, number> = { critical: 3, warning: 2, info: 1 };
        return ((sev[b.severity] || 0) - (sev[a.severity] || 0)) * (sortOrder === "asc" ? -1 : 1);
      } else if (sortKey === "path") {
        return (a.path || "").localeCompare(b.path || "") * (sortOrder === "asc" ? 1 : -1);
      } else if (sortKey === "type") {
        return (a.type || "").localeCompare(b.type || "") * (sortOrder === "asc" ? 1 : -1);
      }
      return 0;
    });
    return out;
  }, [issues, severityFilter, typeFilter, sortKey, sortOrder]);

  // Unique values for filters (as string[])
  const severityOptions: string[] = useMemo(
    () => Array.from(new Set(issues.map((i) => i.severity))).filter(Boolean) as string[],
    [issues]
  );
  const typeOptions: string[] = useMemo(
    () => Array.from(new Set(issues.map((i) => i.type))).filter(Boolean) as string[],
    [issues]
  );

  // Export
  const handleExport = async (format: string) => {
    setExporting(true);
    try {
      const res = await triggerCommand.mutateAsync({
        command: "export_stencil_health",
        params: { format }
      });
      if (res.status === "ok" && res.result?.url) {
        toast.success("Export ready. Downloading...");
        window.open(res.result.url, "_blank");
      } else {
        throw new Error(res.message || "Export failed");
      }
    } catch (e: any) {
      toast.error(`Export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  };

  // Page UI
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading health data...</span>
      </div>
    );
  }
  // Error display
  if (isError) {
    const errorMsg = typeof error === "string" ? error : (error as any)?.message;
    return (
      <div className="text-red-600 bg-red-50 border border-red-300 p-4 rounded flex items-center">
        <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
        <div>
          <p className="font-semibold">Error loading health data:</p>
          <pre className="mt-1 text-sm whitespace-pre-wrap">{errorMsg}</pre>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Stencil Health Monitor</h1>
      {/* Status Summary */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" /> API & Database Health
            </CardTitle>
            <CardDescription>Status of the backend API and database connection.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span>API Status:</span>
              {health ? <StatusBadge status={health.api_status} /> : <Badge variant="secondary">Loading...</Badge>}
            </div>
            <div className="flex items-center justify-between">
              <span>Database Status:</span>
              {health ? <StatusBadge status={health.db_status} /> : <Badge variant="secondary">Loading...</Badge>}
            </div>
            {health?.db_message && (
              <p className="text-sm text-muted-foreground pt-1 border-t mt-3">{health.db_message}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Power className="h-5 w-5" /> Visio Integration
            </CardTitle>
            <CardDescription>Status of the connection to Microsoft Visio.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span>Connection Status:</span>
              {integration ? <StatusBadge status={integration.visio_status} /> : <Badge variant="secondary">Loading...</Badge>}
            </div>
            {integration?.message && !integration.error_message && (
              <p className="text-sm text-muted-foreground pt-1 border-t mt-3">{integration.message}</p>
            )}
            {integration?.error_message && (
              <p className="text-sm text-destructive pt-1 border-t mt-3">{integration.error_message}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Analytics badges */}
      {healthDetail?.summary && (
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <span className="font-semibold">Summary:</span>
          <Badge variant="outline" style={{ background: "var(--chart-1)", color: "#fff" }}>
            Total: {healthDetail.summary.total}
          </Badge>
          <Badge variant="outline" style={{ background: "var(--chart-2)", color: "#fff" }}>
            Empty: {healthDetail.summary.empty}
          </Badge>
          <Badge variant="outline" style={{ background: "var(--chart-3)", color: "#fff" }}>
            Duplicates: {healthDetail.summary.duplicates}
          </Badge>
          <Badge variant="outline" style={{ background: "var(--chart-4)", color: "#fff" }}>
            Errors: {healthDetail.summary.errors}
          </Badge>
          <Button
            className="ml-auto"
            onClick={() => handleExport("csv")}
            disabled={exporting}
            variant="outline"
          >
            {exporting ? "Exporting..." : "Export Health Report"}
          </Button>
        </div>
      )}

      {/* Issue Table with filtering */}
      <div className="mb-2 flex flex-wrap gap-3 items-center">
        <Filter className="h-4 w-4" />
        <label>
          Severity:
          <select
            className="ml-1 mr-2 border rounded px-1 py-0.5 text-sm"
            value={severityFilter || ""}
            onChange={e => setSeverityFilter(e.target.value || null)}
          >
            <option value="">All</option>
            {severityOptions.map((s: string) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Type:
          <select
            className="ml-1 mr-2 border rounded px-1 py-0.5 text-sm"
            value={typeFilter || ""}
            onChange={e => setTypeFilter(e.target.value || null)}
          >
            <option value="">All</option>
            {typeOptions.map((t: string) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Sort:
          <select
            className="ml-1 border rounded px-1 py-0.5 text-sm"
            value={sortKey}
            onChange={e => setSortKey(e.target.value)}
          >
            <option value="severity">Severity</option>
            <option value="path">Path</option>
            <option value="type">Type</option>
          </select>
          <Button
            className="ml-1"
            variant="ghost"
            size="sm"
            onClick={() => setSortOrder(v => v === "asc" ? "desc" : "asc")}
          >
            {sortOrder === "asc" ? "▲" : "▼"}
          </Button>
        </label>
        {(severityFilter || typeFilter) && (
          <Button
            className="ml-2"
            variant="outline"
            size="sm"
            onClick={() => {
              setSeverityFilter(null);
              setTypeFilter(null);
            }}
          >
            <X className="h-3 w-3 mr-1" /> Clear Filters
          </Button>
        )}
      </div>
      <div className="overflow-x-auto rounded-lg border border-border bg-background">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-muted">
              <th className="text-left font-semibold px-4 py-2">Stencil</th>
              <th className="text-left font-semibold px-4 py-2">Issue</th>
              <th className="text-left font-semibold px-4 py-2">Severity</th>
              <th className="text-left font-semibold px-4 py-2">Type</th>
              <th className="text-left font-semibold px-4 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {filteredIssues.map((issue, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? "" : "bg-muted/20"}>
                <td className="px-4 py-2 font-mono truncate max-w-xs">{issue.path}</td>
                <td className="px-4 py-2">{issue.issue}</td>
                <td className="px-4 py-2">
                  <Badge variant={issue.severity === "critical" ? "destructive" : issue.severity === "warning" ? "default" : "secondary"}>
                    {issue.severity}
                  </Badge>
                </td>
                <td className="px-4 py-2">{issue.type}</td>
                <td className="px-4 py-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedIssue(issue);
                      setDetailOpen(true);
                    }}
                  >
                    <Info className="h-4 w-4" />
                  </Button>
                </td>
              </tr>
            ))}
            {filteredIssues.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-muted-foreground">
                  No issues match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Issue Detail Modal */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent>
          <DialogTitle>Stencil Issue Details</DialogTitle>
          <DialogDescription>
            {selectedIssue ? (
              <div className="space-y-2">
                <div>
                  <span className="font-semibold">Path:</span>{" "}
                  <span className="font-mono">{selectedIssue.path}</span>
                </div>
                <div>
                  <span className="font-semibold">Issue:</span>{" "}
                  {selectedIssue.issue}
                </div>
                <div>
                  <span className="font-semibold">Severity:</span>{" "}
                  <Badge variant={selectedIssue.severity === "critical" ? "destructive" : selectedIssue.severity === "warning" ? "default" : "secondary"}>
                    {selectedIssue.severity}
                  </Badge>
                </div>
                <div>
                  <span className="font-semibold">Type:</span>{" "}
                  {selectedIssue.type}
                </div>
                {selectedIssue.details && (
                  <div>
                    <span className="font-semibold">Details:</span>{" "}
                    <span className="font-mono">{selectedIssue.details}</span>
                  </div>
                )}
              </div>
            ) : (
              <span>No issue selected.</span>
            )}
          </DialogDescription>
          <DialogFooter>
            <DialogClose asChild>
              <Button>Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}