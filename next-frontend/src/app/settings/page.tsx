"use client";

import React, { useState } from 'react';
// Updated imports
import {
  useIntegrationStatus,
  useTriggerCommand,
  useDirectoryPaths,
  useActiveDirectory,
  useAddDirectory,
  useSetActiveDirectory,
  useRemoveDirectory,
  ApiError,
  IntegrationStatus,
  CommandPayload,
  CommandResponse,
  DirectoryPath,
  DirectoryPathPayload
} from "@/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Zap,
  RefreshCcw,
  PowerOff,
  Server,
  Database,
  Power,
  FolderInput,
  Plus,
  Trash2,
  Check
} from "lucide-react"; // Added missing icons
import { Badge } from "@/components/ui/badge";
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


  // Directory paths state
  const { data: directories, isLoading: directoriesLoading, isError: directoriesError, error: directoriesErrorData, refetch: refetchDirectories } = useDirectoryPaths();
  const { data: activeDirectory, isLoading: activeDirectoryLoading, refetch: refetchActiveDirectory } = useActiveDirectory();
  
  // Directory mutations
  const addDirectoryMutation = useAddDirectory({
    onSuccess: (data) => {
      toast.success(`Directory '${data.name}' added successfully`);
      refetchDirectories();
    },
    onError: (error: Error | ApiError) => {
      const apiError = error as ApiError;
      toast.error(`Failed to add directory`, {
        description: apiError?.detail || apiError?.message || "An unknown error occurred.",
      });
    },
  });
  
  const setActiveDirectoryMutation = useSetActiveDirectory({
    onSuccess: (data) => {
      toast.success(`Directory '${data.name}' set as active`);
      refetchActiveDirectory();
    },
    onError: (error: Error | ApiError) => {
      const apiError = error as ApiError;
      toast.error(`Failed to set active directory`, {
        description: apiError?.detail || apiError?.message || "An unknown error occurred.",
      });
    },
  });
  
  const removeDirectoryMutation = useRemoveDirectory({
    onSuccess: () => {
      toast.success(`Directory removed successfully`);
      refetchDirectories();
      refetchActiveDirectory();
    },
    onError: (error: Error | ApiError) => {
      const apiError = error as ApiError;
      toast.error(`Failed to remove directory`, {
        description: apiError?.detail || apiError?.message || "An unknown error occurred.",
      });
    },
  });
  
  // Add directory dialog state
  const [isAddDirectoryOpen, setIsAddDirectoryOpen] = useState(false);
  const [newDirectoryPath, setNewDirectoryPath] = useState("");
  const [newDirectoryName, setNewDirectoryName] = useState("");
  
  const handleAddDirectory = () => {
    if (!newDirectoryPath.trim()) {
      toast.error("Directory path is required");
      return;
    }
    
    const payload: DirectoryPathPayload = {
      path: newDirectoryPath,
      name: newDirectoryName.trim() || undefined // Use undefined if empty to let backend use default name
    };
    
    addDirectoryMutation.mutate(payload);
    setIsAddDirectoryOpen(false);
    setNewDirectoryPath("");
    setNewDirectoryName("");
  };
  
  const handleSetActiveDirectory = (directoryId: number) => {
    setActiveDirectoryMutation.mutate(directoryId);
  };
  
  const handleRemoveDirectory = (directoryId: number) => {
    removeDirectoryMutation.mutate(directoryId);
  };
  
  // Render directory paths
  const renderDirectories = () => {
    if (directoriesLoading) {
      return (
        <div className="flex items-center text-muted-foreground">
          <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading directories...
        </div>
      );
    }
    
    if (directoriesError) {
      const errorObj = directoriesErrorData as any;
      let errorMessage = 'Unknown error';
      if (errorObj instanceof ApiError) {
        errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`;
      }
      else if (errorObj instanceof Error) {
        errorMessage = errorObj.message;
      }
      
      return (
        <div className="flex items-center text-destructive">
          <AlertCircle className="h-4 w-4 mr-2" /> Error loading directories: {errorMessage}
        </div>
      );
    }
    
    if (!directories || directories.length === 0) {
      return (
        <div className="text-muted-foreground">
          No directories configured. Add a directory to start scanning stencils.
        </div>
      );
    }
    
    return (
      <div className="space-y-2">
        {directories.map((directory) => (
          <div key={directory.id} className="flex items-center justify-between py-2 border-b border-border">
            <div className="flex-1">
              <div className="font-medium">{directory.name}</div>
              <div className="text-xs text-muted-foreground truncate max-w-[300px]">{directory.path}</div>
            </div>
            <div className="flex items-center space-x-2">
              {directory.is_active ? (
                <Badge variant="default" className="flex items-center gap-1">
                  <Check className="h-3 w-3" />
                  <span>Active</span>
                </Badge>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSetActiveDirectory(directory.id)}
                  disabled={setActiveDirectoryMutation.isPending}
                >
                  Set Active
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => handleRemoveDirectory(directory.id)}
                disabled={removeDirectoryMutation.isPending}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
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

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Directory Paths</CardTitle>
            <CardDescription>Manage directories for stencil scanning.</CardDescription>
          </div>
          <Dialog open={isAddDirectoryOpen} onOpenChange={setIsAddDirectoryOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Add Directory
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Directory Path</DialogTitle>
                <DialogDescription>
                  Add a new directory path to scan for Visio stencils.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <label htmlFor="path">Directory Path</label>
                  <Input
                    id="path"
                    placeholder="C:\Path\To\Stencils"
                    value={newDirectoryPath}
                    onChange={(e) => setNewDirectoryPath(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="name">Display Name (Optional)</label>
                  <Input
                    id="name"
                    placeholder="My Stencils"
                    value={newDirectoryName}
                    onChange={(e) => setNewDirectoryName(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsAddDirectoryOpen(false)}>Cancel</Button>
                <Button onClick={handleAddDirectory} disabled={!newDirectoryPath.trim() || addDirectoryMutation.isPending}>
                  {addDirectoryMutation.isPending ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Adding...</>
                  ) : (
                    <>Add Directory</>
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {renderDirectories()}
          <div className="flex justify-end mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchDirectories();
                refetchActiveDirectory();
              }}
            >
              <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
            </Button>
          </div>
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
                disabled={triggerCommandMutation.isPending}
                className="w-full sm:w-auto"
             >
                {triggerCommandMutation.isPending && triggerCommandMutation.variables?.command === 'trigger_scan' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                 ) : (
                   <Zap className="mr-2 h-4 w-4" />
                 )}
                Trigger Full Stencil Scan
             </Button>
             {activeDirectory && (
               <div className="text-xs text-muted-foreground pt-2">
                 Active scanning directory: <span className="font-medium">{activeDirectory.name}</span> ({activeDirectory.path})
               </div>
             )}
             <p className="text-xs text-muted-foreground">
                Note: Actions interact with the local backend server. Ensure it's running.
                Triggering a scan may take some time depending on the number of stencils.
             </p>
         </CardContent>
      </Card>
    </div>
  );
}