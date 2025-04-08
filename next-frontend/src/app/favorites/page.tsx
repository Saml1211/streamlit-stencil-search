"use client";

import React from 'react';
// Import ApiError for better error handling
import { useFavorites, useRemoveFavorite, FavoriteItem, ApiError } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, Trash2, AlertCircle, Shapes, FileText } from "lucide-react"; // Added icons
import { useQueryClient } from '@tanstack/react-query';
import { toast } from "sonner"; // Import sonner toast

export default function FavoritesPage() {
  const queryClient = useQueryClient();
  const { data: favorites, isLoading, isError, error } = useFavorites();

  const removeFavoriteMutation = useRemoveFavorite({
    onSuccess: (_, variables) => { // variables contains the favId passed to mutate
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
      toast.success("Favorite Removed", {
        description: `Item removed from favorites.`
      });
      console.log(`Favorite removed successfully: ID ${variables}`);
    },
    onError: (err, variables) => {
       const apiError = err as ApiError;
       toast.error("Error Removing Favorite", {
         description: apiError?.detail || apiError?.message || "Could not remove favorite.",
       });
       console.error(`Failed to remove favorite ID ${variables}:`, err);
    }
  });

  // Correct type hint for fav.id (should be number from backend)
  const handleRemove = (id: number) => {
    removeFavoriteMutation.mutate(id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading favorites...</span>
      </div>
    );
  }

  if (isError) {
     const errorObj = error as any;
     let errorMessage = 'Unknown error';
     if (errorObj instanceof ApiError) {
          errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`;
      } else if (errorObj instanceof Error) {
          errorMessage = errorObj.message;
      }
    return (
      <div className="text-red-600 bg-red-50 border border-red-300 p-4 rounded flex items-center">
         <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
         <div>
           <p className="font-semibold">Error loading favorites:</p>
           <pre className="mt-1 text-sm whitespace-pre-wrap">{errorMessage}</pre>
         </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Favorites</h1>
       {(!favorites || favorites.length === 0) ? (
           <p className="text-muted-foreground">You haven't added any favorites yet.</p>
       ) : (
       <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
         {favorites.map((fav) => (
           <Card key={fav.id} className="flex flex-col">
             <CardHeader className="pb-2">
               <CardTitle className="text-base font-medium truncate flex items-center gap-2">
                  {fav.item_type === 'shape' ? <Shapes className="h-4 w-4 text-muted-foreground" /> : <FileText className="h-4 w-4 text-muted-foreground" />}
                  {/* Display actual names now available from JOIN */}
                  {/* Provide fallback for potentially null/undefined names in title */}
                  <span title={(fav.item_type === 'shape' ? fav.shape_name : fav.stencil_name) ?? ''}>
                      {fav.item_type === 'shape' ? fav.shape_name : fav.stencil_name}
                  </span>
               </CardTitle>
               <CardDescription className="text-xs truncate" title={fav.stencil_path}>
                   {/* Show stencil path for context */}
                   In: {fav.stencil_name || fav.stencil_path}
                   {fav.item_type === 'stencil' && ` (${fav.id})`} {/* Show fav ID for stencils if needed */}
                   {fav.item_type === 'shape' && ` (Shape ID: ${fav.shape_id}, Fav ID: ${fav.id})`} {/* Show IDs */}
               </CardDescription>
             </CardHeader>
             <CardContent className="mt-auto"> {/* Push button to bottom */}
               <Button
                 variant="outline"
                 size="sm"
                 className="w-full text-red-600 hover:bg-red-50 hover:text-red-700"
                 onClick={() => handleRemove(fav.id)}
                 disabled={removeFavoriteMutation.isPending && removeFavoriteMutation.variables === fav.id}
               >
                 {removeFavoriteMutation.isPending && removeFavoriteMutation.variables === fav.id ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                 ) : (
                   <Trash2 className="mr-2 h-4 w-4" />
                 )}
                 Remove
               </Button>
             </CardContent>
           </Card>
         ))}
       </div>
       )}
    </div>
  );
}