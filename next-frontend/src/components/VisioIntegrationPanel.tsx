"use client";

import React, { useState } from "react";
import { useIntegrationStatus, useImportContent, useTriggerCommand } from "@/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogFooter, AlertDialogAction, AlertDialogCancel } from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Loader2, RefreshCcw, CheckCircle, XCircle, PlugZap, Monitor } from "lucide-react";

export function VisioIntegrationPanel() {
  const { data: integrationStatus, isLoading: statusLoading, isError: statusError, refetch } = useIntegrationStatus();
  const [showError, setShowError] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // --- Session Selection State ---
  // MOCK: This should eventually come from the backend.
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [availableSessions, setAvailableSessions] = useState([
    { id: "visio-1", name: "Visio (PID 1001) - Drawing1.vsdx", isActive: true },
    { id: "visio-2", name: "Visio (PID 1027) - NetworkDiagram.vsdx", isActive: false },
    { id: "visio-3", name: "Visio (PID 1089) - FloorPlan.vsdx", isActive: false }
  ]);

  // For shape import (placeholder)
  const importMutation = useImportContent({
    onSuccess: (data) => {
      setErrorMsg(null);
      setShowError(false);
    },
    onError: (error) => {
      setErrorMsg(error.detail || error.message);
      setShowError(true);
    }
  });

  // Actions using command API (refresh, session switch, remote connect)
  const commandMutation = useTriggerCommand({
    onSuccess: (data) => {
      setActionLoading(false);
      refetch();
      setErrorMsg(null);
      setShowError(false);
    },
    onError: (error) => {
      setActionLoading(false);
      setErrorMsg(error.detail || error.message);
      setShowError(true);
    }
  });

  // Refresh Visio status/sessions
  const handleRefresh = () => {
    setActionLoading(true);
    commandMutation.mutate({ command: "refresh_visio_status" });
  };

  // Import Shape (demo)
  const handleImportShape = () => {
    setActionLoading(true);
    importMutation.mutate({
      type: "text",
      content: "Sample Import Content",
      metadata: { source_url: "N/A", capture_time: new Date().toISOString() }
    });
  };

  // Open session select modal
  const handleOpenSessionModal = () => {
    setShowSessionModal(true);
  };

  // Session switch (calls backend then updates UI)
  const handleSwitchSession = (sessionId: string) => {
    setActionLoading(true);
    setActiveSessionId(sessionId);
    commandMutation.mutate({
      command: "switch_visio_session",
      params: { session_id: sessionId }
    });
    // Update local mock state:
    setAvailableSessions(
      availableSessions.map((s) => ({
        ...s,
        isActive: s.id === sessionId
      }))
    );
    setShowSessionModal(false);
  };

  let statusContent = null;
  let currentSessionName = null;

  if (statusLoading) {
    statusContent = (
      <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="animate-spin h-5 w-5" /> Checking Visio status...</div>
    );
  } else if (statusError || !integrationStatus) {
    statusContent = (
      <div className="flex items-center text-destructive gap-2">
        <XCircle className="h-5 w-5" />
        <span>Visio integration unavailable</span>
        <Button size="sm" variant="outline" onClick={() => refetch()}>Retry</Button>
      </div>
    );
  } else {
    const statusColor =
      integrationStatus.visio_status === "connected" ? "text-green-600" :
      integrationStatus.visio_status === "error" ? "text-destructive" : "text-yellow-600";

    const statusIcon =
      integrationStatus.visio_status === "connected" ? <CheckCircle className="h-5 w-5" /> :
      integrationStatus.visio_status === "error" ? <XCircle className="h-5 w-5" /> :
      <PlugZap className="h-5 w-5" />;

    // Find active session for UI (mock local for now)
    const active = availableSessions.find((s) => s.isActive);
    currentSessionName = active ? active.name : null;

    statusContent = (
      <div className={`flex items-center gap-2 ${statusColor}`}>
        {statusIcon}
        <span className="font-medium">{integrationStatus.visio_status.charAt(0).toUpperCase() + integrationStatus.visio_status.slice(1)}</span>
        {integrationStatus.message && (
          <span className="ml-2 text-xs text-muted-foreground">{integrationStatus.message}</span>
        )}
        <Button size="icon" variant="ghost" title="Refresh" onClick={handleRefresh} disabled={actionLoading}>
          <RefreshCcw className={`h-4 w-4 ${actionLoading ? "animate-spin" : ""}`} />
        </Button>
      </div>
    );
  }

  return (
    <>
      <Card className="mb-6 p-4 border-2 border-primary/50 bg-muted/20">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold mb-1">Visio Integration</h2>
            {statusContent}
            <div className="mt-1 flex items-center gap-2">
              <Monitor className="h-4 w-4 text-primary" />
              <span className="text-sm">
                {currentSessionName
                  ? <>Active Session: <strong>{currentSessionName}</strong></>
                  : <span className="text-muted-foreground">No active session</span>
                }
              </span>
              <Button size="sm" variant="outline" onClick={handleOpenSessionModal} disabled={statusLoading || statusError || !integrationStatus || actionLoading}>
                Switch Session
              </Button>
            </div>
          </div>
          <div className="flex gap-2 mt-2 md:mt-0">
            <Button
              size="sm"
              variant="secondary"
              disabled={statusLoading || statusError || !integrationStatus || actionLoading}
              onClick={handleImportShape}
            >
              Import Shape (Demo)
            </Button>
            {/* Additional buttons for: Open Visio, Remote Connect, etc. */}
          </div>
        </div>
      </Card>
      {/* Session Selection Dialog */}
      <Dialog open={showSessionModal} onOpenChange={setShowSessionModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Select Active Visio Session</DialogTitle>
          </DialogHeader>
          {availableSessions.length === 0 ? (
            <div>No Visio sessions detected.</div>
          ) : (
            <div className="space-y-2 mt-2">
              {availableSessions.map((session) => (
                <Button
                  key={session.id}
                  variant={session.isActive ? "default" : "outline"}
                  disabled={session.isActive || actionLoading}
                  className="w-full justify-start"
                  onClick={() => handleSwitchSession(session.id)}
                >
                  {session.name}
                  {session.isActive && (
                    <span className="ml-2 text-green-600 text-xs font-semibold">Active</span>
                  )}
                </Button>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowSessionModal(false)}>Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Error Dialog */}
      <AlertDialog open={showError} onOpenChange={setShowError}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Visio Integration Error</AlertDialogTitle>
          </AlertDialogHeader>
          <div className="text-destructive">{errorMsg}</div>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setShowError(false)}>OK</AlertDialogAction>
            <AlertDialogCancel asChild>
              <Button variant="ghost" onClick={() => setShowError(false)}>Close</Button>
            </AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}