"use client";

import React from 'react';
// Import correct hooks and error type
import { useHealthStatus, useIntegrationStatus, ApiError, HealthStatus, IntegrationStatus } from "@/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, AlertCircle, CheckCircle, Server, Database, Power, PowerOff } from "lucide-react";
import { Badge } from "@/components/ui/badge"; // Import Badge

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

  const isLoading = isLoadingHealth || isLoadingIntegration;
  const isError = isErrorHealth || isErrorIntegration;
  const error = errorHealth || errorIntegration; // Show first error encountered

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading status...</span>
      </div>
    );
  }

  // Combine error display
  if (isError) {
     const errorObj = error as any;
     let errorMessage = 'Unknown error';
     if (errorObj instanceof ApiError) { errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`; }
     else if (errorObj instanceof Error) { errorMessage = errorObj.message; }
    return (
       <div className="text-red-600 bg-red-50 border border-red-300 p-4 rounded flex items-center">
          <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
          <div>
            <p className="font-semibold">Error loading status:</p>
            <pre className="mt-1 text-sm whitespace-pre-wrap">{errorMessage}</pre>
          </div>
       </div>
     );
  }

  // Render status cards only if data is available
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">System Status</h1>
      <div className="grid gap-6 md:grid-cols-2">
          {/* API & DB Health Card */}
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

          {/* Visio Integration Card */}
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
      {/* TODO: Add buttons for actions like Recheck Status, Clear Cache etc. */}
    </div>
  );
}