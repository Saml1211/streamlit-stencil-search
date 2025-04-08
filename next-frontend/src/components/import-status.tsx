"use client";

import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader2, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

// Example: Simulate receiving status updates (replace with actual mechanism later)
type ImportStatus = 'idle' | 'pending' | 'success' | 'error';
interface SimulatedStatus {
    status: ImportStatus;
    message?: string;
    timestamp: number;
}

// Placeholder hook - replace with actual API/event listener later
function useSimulatedImportStatus(): SimulatedStatus {
  const [status, setStatus] = useState<SimulatedStatus>({ status: 'idle', timestamp: Date.now() });

  // Simulate an import happening every 15 seconds for demo
  useEffect(() => {
    const intervalId = setInterval(() => {
      setStatus({ status: 'pending', message: 'Importing data...', timestamp: Date.now() });
      const delay = Math.random() * 2000 + 500; // Random delay
      setTimeout(() => {
        const success = Math.random() > 0.3; // 70% success rate
        setStatus({
          status: success ? 'success' : 'error',
          message: success ? 'Import successful!' : 'Import failed: Visio not found.',
          timestamp: Date.now(),
        });
        // Reset to idle after a few seconds
        setTimeout(() => setStatus({ status: 'idle', timestamp: Date.now() }), 3000);
      }, delay);
    }, 15000); // Trigger every 15s

    return () => clearInterval(intervalId);
  }, []);

  return status;
}


export function ImportStatusIndicator() {
  const latestStatus = useSimulatedImportStatus(); // Replace with real hook later
  const [visible, setVisible] = useState(false);

  useEffect(() => {
     // Show indicator when not idle, hide after a few seconds of being idle again
     if (latestStatus.status !== 'idle') {
       setVisible(true);
     } else {
       const timer = setTimeout(() => setVisible(false), 3000); // Hide after 3s of idle
       return () => clearTimeout(timer);
     }
  }, [latestStatus.status, latestStatus.timestamp]); // Depend on timestamp to re-trigger effect


  if (!visible) {
    return null; // Don't render anything if idle for a while
  }

  const getStatusContent = () => {
    switch (latestStatus.status) {
      case 'pending':
        return { icon: <Loader2 className="h-4 w-4 animate-spin" />, text: latestStatus.message || 'Importing...', bg: 'bg-blue-100', textClr: 'text-blue-800' };
      case 'success':
        return { icon: <CheckCircle className="h-4 w-4" />, text: latestStatus.message || 'Import successful!', bg: 'bg-green-100', textClr: 'text-green-800' };
      case 'error':
        return { icon: <XCircle className="h-4 w-4" />, text: latestStatus.message || 'Import failed!', bg: 'bg-red-100', textClr: 'text-red-800' };
      case 'idle':
      default:
         // Render a subtle idle state briefly before hiding
         return { icon: <Info className="h-4 w-4" />, text: 'Ready for import', bg: 'bg-gray-100', textClr: 'text-gray-600' };
    }
  };

  const { icon, text, bg, textClr } = getStatusContent();

  // Simple status bar at the bottom or top
  return (
    <div className={cn(
        "fixed bottom-4 right-4 p-3 rounded-md shadow-md text-sm flex items-center space-x-2 z-50 transition-opacity duration-300",
        bg,
        textClr,
        visible ? 'opacity-100' : 'opacity-0' // Fade in/out
       )}
       aria-live="polite"
     >
      {icon}
      <span>{text}</span>
    </div>
  );
}