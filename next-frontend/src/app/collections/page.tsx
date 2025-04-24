"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  useCollections,
  useCreateCollection,
  useDeleteCollection,
  useCollectionDetails,
  useUpdateCollection,
  useSearchShapes,
  Collection,
  ApiError,
  CreateCollectionPayload,
  UpdateCollectionPayload,
  CollectionShapeSummary,
  ShapeSummary
} from "@/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, Trash2, AlertCircle, PlusCircle, X, Eye, Search, Plus } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { useQueryClient } from '@tanstack/react-query';
import { toast } from "sonner";

// Hook for debouncing search input
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => { setDebouncedValue(value); }, delay);
    return () => { clearTimeout(handler); };
  }, [value, delay]);
  return debouncedValue;
}

// --- Collection Detail View Component ---
function CollectionDetailView({ collectionId }: { collectionId: number }) {
  const queryClient = useQueryClient();
  const { data: details, isLoading, isError, error } = useCollectionDetails(collectionId);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  // Search shapes hook
  const { data: searchResults, isLoading: searchLoading } = useSearchShapes(
    debouncedSearchTerm,
    1,
    10,
    {
      enabled: showSearchResults && debouncedSearchTerm.length > 2,
    }
  );

  // Mutation for updating (adding/removing shapes)
  const updateCollectionMutation = useUpdateCollection({
     onSuccess: (updatedCollection) => {
        toast.success("Collection Updated", {
          description: updateCollectionMutation.variables?.payload.remove_shape_ids
            ? "Shape removed from collection."
            : "Shape added to collection."
        });
        // Invalidate both the detail view and the main list
        queryClient.invalidateQueries({ queryKey: ['collectionDetail', collectionId] });
        queryClient.invalidateQueries({ queryKey: ['collections'] });
        // Clear search when adding shapes
        if (updateCollectionMutation.variables?.payload.add_shape_ids) {
          setSearchTerm('');
          setShowSearchResults(false);
        }
     },
     onError: (error) => {
        const apiError = error as ApiError;
        toast.error("Error Updating Collection", {
          description: apiError?.detail || apiError?.message || "Could not update collection."
        });
     }
  });

  const handleRemoveShape = (shapeId: number) => {
     updateCollectionMutation.mutate({
        id: collectionId,
        payload: { remove_shape_ids: [shapeId] }
     });
  };

  const handleAddShape = (shapeId: number) => {
    updateCollectionMutation.mutate({
      id: collectionId,
      payload: { add_shape_ids: [shapeId] }
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
      
      {/* Search input for adding shapes */}
      <div className="mt-4 mb-4">
        <div className="flex gap-2">
          <div className="relative flex-grow">
            <Input
              placeholder="Search for shapes to add..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                if (e.target.value.length > 0) {
                  setShowSearchResults(true);
                }
              }}
              className="pr-8"
              onFocus={() => {
                if (searchTerm.length > 0) {
                  setShowSearchResults(true);
                }
              }}
            />
            {searchLoading && (
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={() => {
              setShowSearchResults(!showSearchResults);
              if (!showSearchResults && searchTerm.length === 0) {
                setSearchTerm('');
              }
            }}
          >
            <Search className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {/* Search results */}
      {showSearchResults && searchTerm.length > 0 && (
        <div className="border rounded-md mb-4 max-h-[200px] overflow-y-auto">
          <div className="p-2 bg-muted/50 border-b">
            <h4 className="text-sm font-medium">Search Results</h4>
          </div>
          {searchLoading ? (
            <div className="flex justify-center items-center p-4">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm text-muted-foreground">Searching...</span>
            </div>
          ) : !searchResults || searchResults.results.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4 text-center">No shapes found</p>
          ) : (
            <ul className="divide-y">
              {searchResults.results.map((shape) => (
                <li key={shape.shape_id} className="flex justify-between items-center p-2 hover:bg-muted/30">
                  <div>
                    <p className="text-sm font-medium">{shape.shape_name}</p>
                    <p className="text-xs text-muted-foreground">{shape.stencil_name}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAddShape(shape.shape_id)}
                    disabled={updateCollectionMutation.isPending}
                    className="h-8 w-8 p-0"
                  >
                    {updateCollectionMutation.isPending &&
                     updateCollectionMutation.variables?.payload.add_shape_ids?.includes(shape.shape_id) ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      
      {/* Collection shapes list */}
      <div className="mt-2 max-h-[300px] overflow-y-auto pr-2">
        <div className="p-2 bg-muted/50 rounded-md mb-2">
          <h4 className="text-sm font-medium">Shapes in Collection</h4>
        </div>
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
             <DialogContent className="sm:max-w-[700px]">
                <DialogHeader>
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