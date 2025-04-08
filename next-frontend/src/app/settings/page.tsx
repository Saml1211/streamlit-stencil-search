"use client";

import React from 'react';
// Updated imports
import { useIntegrationStatus, useTriggerCommand, ApiError, IntegrationStatus, CommandPayload, CommandResponse } from "@/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, AlertCircle, CheckCircle, XCircle, Zap, RefreshCcw, PowerOff, Server, Database, Power } from "lucide-react"; // Added missing icons
import { Badge } from "@/components/ui/badge"; // Ensure Badge is imported if StatusBadge is used elsewhere or added here
import { toast } from "sonner"; // Import sonner toast

// Helper Status Badge (copied from health page for consistency, or move to shared location)
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
  } else {
     text = status; // Display unknown status as text
  }

  return (
    <Badge variant={variant} className="flex items-center gap-1 w-fit">
       <Icon className="h-3 w-3" />
       <span>{text}</span>
    </Badge>
  );
};


export default function SettingsPage() {
  const { data: status, isLoading, isError, error, refetch } = useIntegrationStatus();

  // Use the correct mutation hook and add onSuccess/onError for feedback
  const triggerCommandMutation = useTriggerCommand({
      onSuccess: (data: CommandResponse, variables: CommandPayload) => {
          toast.success(`Command '${variables.command}' executed`, {
              description: data.message || "Action completed successfully.",
              // Optional: Display result if needed: JSON.stringify(data.result)
          });
      },
      onError: (error: Error | ApiError, variables: CommandPayload) => {
          const apiError = error as ApiError;
          toast.error(`Command '${variables.command}' failed`, {
              description: apiError?.detail || apiError?.message || "An unknown error occurred.",
          });
      },
  });

  // Update handler to use correct payload structure
  const handleTriggerAction = (commandName: string, params?: Record<string, any>) => {
     const payload: CommandPayload = { command: commandName, params: params || null };
     triggerCommandMutation.mutate(payload);
  };

  const renderStatus = () => {
    if (isLoading) {
      return (
        <div className="flex items-center text-muted-foreground">
          <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Checking status...
        </div>
      );
    }
    if (isError) {
       const errorObj = error as any;
       let errorMessage = 'Unknown error';
       if (errorObj instanceof ApiError) { errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`; }
       else if (errorObj instanceof Error) { errorMessage = errorObj.message; }
      return (
        <div className="flex items-center text-destructive">
          <AlertCircle className="h-4 w-4 mr-2" /> Error checking status: {errorMessage}
        </div>
      );
    }
    if (!status) {
       return <div className="text-muted-foreground">Status unavailable.</div>;
    }

    // Display using StatusBadge for consistency
    return (
      <div className="space-y-2 text-sm">
         <div className="flex items-center justify-between">
             <span>Visio Connection:</span>
             <StatusBadge status={status.visio_status} />
         </div>
         {status.message && !status.error_message && <p className="text-xs text-muted-foreground">{status.message}</p>}
         {status.error_message && <p className="text-xs text-destructive">{status.error_message}</p>}
      </div>
    );
  };


  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Settings & Integration</h1>

      <Card className="mb-6">
         <CardHeader>
            <CardTitle>Integration Status</CardTitle>
            <CardDescription>Current status of the connection to Microsoft Visio.</CardDescription>
         </CardHeader>
         <CardContent>
            {renderStatus()}
            <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-4">
               <RefreshCcw className="mr-2 h-4 w-4" /> Refresh Status
            </Button>
         </CardContent>
      </Card>

      <Card>
         <CardHeader>
            <CardTitle>Actions</CardTitle>
            <CardDescription>Trigger backend operations.</CardDescription>
         </CardHeader>
         <CardContent className="space-y-3">
             <Button
                onClick={() => handleTriggerAction('trigger_scan')}
                // Check mutation status correctly
                disabled={triggerCommandMutation.isPending}
                className="w-full sm:w-auto"
             >
                {/* Check mutation status and specific command if needed */}
                {triggerCommandMutation.isPending && triggerCommandMutation.variables?.command === 'trigger_scan' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                 ) : (
                   <Zap className="mr-2 h-4 w-4" />
                 )}
                Trigger Full Stencil Scan
             </Button>
             {/* TODO: Add button/input for scanning specific directory */}
              <p className="text-xs text-muted-foreground pt-2">
                 Note: Actions interact with the local backend server. Ensure it's running.
                 Triggering a scan may take some time depending on the number of stencils.
              </p>
         </CardContent>
      </Card>

    </div>
  );
}