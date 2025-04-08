"use client";

import React, { useState, useCallback } from 'react';
import {
  useCollections,
  useCreateCollection,
  useDeleteCollection,
  useCollectionDetails,
  useUpdateCollection, // Hook for adding/removing shapes
  Collection,
  ApiError,
  CreateCollectionPayload,
  UpdateCollectionPayload,
  CollectionShapeSummary
} from "@/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, Trash2, AlertCircle, PlusCircle, X, Eye } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { useQueryClient } from '@tanstack/react-query';
import { toast } from "sonner";

// --- Collection Detail View Component ---
function CollectionDetailView({ collectionId }: { collectionId: number }) {
  const queryClient = useQueryClient();
  const { data: details, isLoading, isError, error } = useCollectionDetails(collectionId);

  // Mutation for updating (removing shapes)
  const updateCollectionMutation = useUpdateCollection({
     onSuccess: (updatedCollection) => {
        toast.success("Shape Removed", { description: `Shape removed from collection '${updatedCollection.name}'.` });
        // Invalidate both the detail view and the main list
        queryClient.invalidateQueries({ queryKey: ['collectionDetail', collectionId] });
        queryClient.invalidateQueries({ queryKey: ['collections'] });
     },
     onError: (error) => {
        const apiError = error as ApiError;
        toast.error("Error Removing Shape", { description: apiError?.detail || apiError?.message || "Could not remove shape." });
     }
  });

  const handleRemoveShape = (shapeId: number) => {
     updateCollectionMutation.mutate({
        id: collectionId,
        payload: { remove_shape_ids: [shapeId] }
     });
  };

  if (isLoading) return <div className="flex justify-center items-center p-8"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  if (isError) {
     const errorObj = error as any;
     let errorMessage = 'Unknown error';
     if (errorObj instanceof ApiError) { errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`; }
     else if (errorObj instanceof Error) { errorMessage = errorObj.message; }
     return <div className="text-red-600 p-4">Error loading collection details: {errorMessage}</div>;
  }
  if (!details) return <div className="p-4">Collection details not found.</div>;

  return (
    <div>
      <DialogDescription>Manage shapes in this collection.</DialogDescription>
      <div className="mt-4 max-h-[60vh] overflow-y-auto pr-2">
        {details.shapes && details.shapes.length > 0 ? (
          <ul className="space-y-2">
            {details.shapes.map((shape) => (
              <li key={shape.shape_id} className="flex justify-between items-center p-2 border rounded-md hover:bg-muted/50">
                <div>
                  <p className="font-medium">{shape.shape_name}</p>
                  <p className="text-xs text-muted-foreground" title={shape.stencil_path}>{shape.stencil_name || 'Unknown Stencil'}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleRemoveShape(shape.shape_id)}
                  disabled={updateCollectionMutation.isPending && updateCollectionMutation.variables?.payload?.remove_shape_ids?.includes(shape.shape_id)}
                  title="Remove shape from collection"
                >
                   {updateCollectionMutation.isPending && updateCollectionMutation.variables?.payload?.remove_shape_ids?.includes(shape.shape_id) ? (
                       <Loader2 className="h-4 w-4 animate-spin" />
                   ) : (
                       <X className="h-4 w-4" />
                   )}
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-center py-4">This collection is empty.</p>
        )}
      </div>
       {/* TODO: Add Input/Button here to search and add shapes? */}
    </div>
  );
}


// --- Main Collections Page Component ---
export default function CollectionsPage() {
  const queryClient = useQueryClient();
  const [newCollectionName, setNewCollectionName] = useState('');
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);

  const { data: collections, isLoading, isError, error } = useCollections();

  const createCollectionMutation = useCreateCollection({
    onSuccess: (newCollection) => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      setNewCollectionName('');
      toast.success("Collection Created", { description: `Collection '${newCollection.name}' created.` });
    },
    onError: (error) => {
      const apiError = error as ApiError;
      toast.error("Failed to Create Collection", { description: apiError?.detail || apiError?.message || "Could not create collection." });
    }
  });

  const deleteCollectionMutation = useDeleteCollection({
     onSuccess: (_, variables) => { // variables = collectionId passed to mutate
        queryClient.invalidateQueries({ queryKey: ['collections'] });
        // If the deleted collection's detail view was open, close it
        if (selectedCollectionId === variables) {
            setSelectedCollectionId(null);
        }
        toast.success("Collection Deleted", { description: `Collection deleted successfully.` });
     },
     onError: (error, variables) => {
        const apiError = error as ApiError;
        toast.error("Failed to Delete Collection", { description: apiError?.detail || apiError?.message || "Could not delete collection." });
     }
  });

  const handleCreateCollection = (e: React.FormEvent) => {
     e.preventDefault();
     if (!newCollectionName.trim()) return;
     createCollectionMutation.mutate({ name: newCollectionName.trim() });
  };

   const handleDeleteCollection = (id: number) => {
     // Confirmation is handled by AlertDialog trigger
     deleteCollectionMutation.mutate(id);
   };


  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading collections...</span>
      </div>
    );
  }

  if (isError) {
      const errorObj = error as any;
      let errorMessage = 'Unknown error';
      if (errorObj instanceof ApiError) { errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`; }
      else if (errorObj instanceof Error) { errorMessage = errorObj.message; }
     return (
       <div className="text-red-600 bg-red-50 border border-red-300 p-4 rounded flex items-center">
          <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
          <div>
            <p className="font-semibold">Error loading collections:</p>
            <pre className="mt-1 text-sm whitespace-pre-wrap">{errorMessage}</pre>
          </div>
       </div>
     );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Collections</h1>

       {/* Create Collection Form */}
       <form onSubmit={handleCreateCollection} className="mb-6 flex gap-2 max-w-sm">
          <Input
             type="text"
             placeholder="New collection name..."
             value={newCollectionName}
             onChange={(e) => setNewCollectionName(e.target.value)}
             disabled={createCollectionMutation.isPending}
          />
          <Button type="submit" disabled={!newCollectionName.trim() || createCollectionMutation.isPending}>
             {createCollectionMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
             ) : (
                <PlusCircle className="mr-2 h-4 w-4" />
             )}
             Create
          </Button>
       </form>

       {/* Collections List */}
       {(!collections || collections.length === 0) ? (
         <p className="text-muted-foreground">No collections created yet.</p>
       ) : (
         <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
           {collections.map((col) => (
             <Card key={col.id}>
               <CardHeader>
                 <CardTitle className="text-base truncate">{col.name}</CardTitle>
                 <CardDescription>
                   {/* Use shape_count from API */}
                   {col.shape_count ?? 0} shape(s) - Updated: {new Date(col.updated_at).toLocaleDateString()}
                 </CardDescription>
               </CardHeader>
               <CardContent className="flex justify-end gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedCollectionId(col.id)}>
                      <Eye className="mr-2 h-4 w-4" /> View Shapes
                  </Button>
                  <AlertDialog>
                     <AlertDialogTrigger asChild>
                         <Button
                           variant="destructive"
                           size="sm"
                           disabled={deleteCollectionMutation.isPending && deleteCollectionMutation.variables === col.id}
                          >
                           {deleteCollectionMutation.isPending && deleteCollectionMutation.variables === col.id ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                           ) : (
                             <Trash2 className="mr-2 h-4 w-4" />
                           )}
                          Delete
                         </Button>
                     </AlertDialogTrigger>
                     <AlertDialogContent>
                       <AlertDialogHeader>
                         <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                         <AlertDialogDescription>
                           This action cannot be undone. This will permanently delete the collection "{col.name}"
                           and remove all associated shapes.
                         </AlertDialogDescription>
                       </AlertDialogHeader>
                       <AlertDialogFooter>
                         <AlertDialogCancel>Cancel</AlertDialogCancel>
                         <AlertDialogAction
                            onClick={() => handleDeleteCollection(col.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                         >
                            Delete
                         </AlertDialogAction>
                       </AlertDialogFooter>
                     </AlertDialogContent>
                   </AlertDialog>
               </CardContent>
             </Card>
           ))}
         </div>
       )}

        {/* Dialog for Viewing/Managing Collection Shapes */}
        <Dialog open={selectedCollectionId !== null} onOpenChange={(open) => !open && setSelectedCollectionId(null)}>
             <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                   {/* Fetch name inside detail view or pass it */}
                   <DialogTitle>Manage Collection Shapes</DialogTitle>
                </DialogHeader>
                {selectedCollectionId && <CollectionDetailView collectionId={selectedCollectionId} />}
                <DialogFooter>
                   <DialogClose asChild>
                      <Button variant="outline">Close</Button>
                   </DialogClose>
                </DialogFooter>
             </DialogContent>
        </Dialog>
    </div>
  );
}