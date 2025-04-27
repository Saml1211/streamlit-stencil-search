"use client";

import React, { useState } from "react";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "../../components/ui/alert-dialog";
import { useTriggerCommand } from "../../api/index";
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";

interface TempFile {
  path: string;
  size: number;
  modified: string;
}

export default function TempFileCleanerPage() {
  const [tempFiles, setTempFiles] = useState<TempFile[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [scanning, setScanning] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const triggerCommand = useTriggerCommand();

  // Scan for temp files
  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await triggerCommand.mutateAsync({ command: "scan_temp_files" });
      if (res.status === "ok" && Array.isArray(res.result)) {
        setTempFiles(res.result as TempFile[]);
        setSelected(new Set());
        toast.success("Scan complete");
      } else {
        throw new Error(res.message || "Unknown error");
      }
    } catch (e: any) {
      toast.error(`Scan failed: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  // Remove selected files
  const handleRemove = async () => {
    setRemoving(true);
    setConfirmOpen(false);
    try {
      const toDelete = Array.from(selected);
      const res = await triggerCommand.mutateAsync({
        command: "delete_temp_files",
        params: { paths: toDelete },
      });
      if (res.status === "ok") {
        toast.success("Files removed");
        setTempFiles((prev) => prev.filter(f => !selected.has(f.path)));
        setSelected(new Set());
      } else {
        throw new Error(res.message || "Unknown error");
      }
    } catch (e: any) {
      toast.error(`Removal failed: ${e.message}`);
    } finally {
      setRemoving(false);
    }
  };

  const handleSelect = (path: string) => {
    setSelected((prev) => {
      const copy = new Set(prev);
      if (copy.has(path)) copy.delete(path);
      else copy.add(path);
      return copy;
    });
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4 flex items-center">
        Temp File Cleaner
        <Badge className="ml-2">Tool</Badge>
      </h1>
      <p className="mb-4 text-muted-foreground">
        Find and remove temporary/corrupted Visio files. Scanning may take a few moments.
      </p>
      <div className="flex gap-4 mb-6">
        <Button onClick={handleScan} disabled={scanning || removing}>
          {scanning ? "Scanning..." : "Scan for Temp Files"}
        </Button>
        {tempFiles.length > 0 && (
          <Button
            variant="destructive"
            disabled={selected.size === 0 || removing}
            onClick={() => setConfirmOpen(true)}
          >
            {removing ? "Removing..." : `Remove Selected (${selected.size})`}
          </Button>
        )}
      </div>

      {tempFiles.length === 0 && !scanning ? (
        <Card className="p-8 text-center text-muted-foreground">
          No temporary files found. Run a scan to search for temp files.
        </Card>
      ) : (
        <div className="space-y-2">
          {tempFiles.map((file) => (
            <Card
              key={file.path}
              className={`flex items-center justify-between p-4 cursor-pointer ${
                selected.has(file.path) ? "border-primary border-2" : ""
              }`}
              onClick={() => handleSelect(file.path)}
            >
              <div>
                <div className="truncate font-mono text-sm">{file.path}</div>
                <div className="text-xs text-muted-foreground">
                  {Math.round(file.size / 1024)} KB &middot; Modified {file.modified}
                </div>
              </div>
              <input
                type="checkbox"
                checked={selected.has(file.path)}
                onChange={() => handleSelect(file.path)}
                onClick={e => e.stopPropagation()}
                aria-label="Select file"
              />
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Remove Files?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to remove the selected temporary files? This cannot be undone.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel asChild>
              <Button variant="outline" onClick={() => setConfirmOpen(false)}>
                Cancel
              </Button>
            </AlertDialogCancel>
            <AlertDialogAction asChild>
              <Button variant="destructive" onClick={handleRemove} disabled={removing}>
                {removing ? "Removing..." : "Remove"}
              </Button>
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}