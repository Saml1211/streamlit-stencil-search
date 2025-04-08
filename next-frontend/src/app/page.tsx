"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { Loader2, Heart, Eye } from "lucide-react";
// Correctly import hooks, types, and ApiError
import { useSearchShapes, useShapeDetail, useAddFavorite, ShapeSummary, ApiError, AddFavoritePayload, FavoriteItem } from "@/api";
import { toast } from "sonner"; // Use sonner

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => { setDebouncedValue(value); }, delay);
    return () => { clearTimeout(handler); };
  }, [value, delay]);
  return debouncedValue;
}

// Component to show shape details in the dialog
function ShapeDetailView({ shapeId }: { shapeId: number }) {
  const { data: shapeDetail, isLoading, isError, error } = useShapeDetail(shapeId);

  if (isLoading) return <div className="flex justify-center items-center p-4"><Loader2 className="h-5 w-5 animate-spin" /></div>;
  // Refined error handling for 'unknown' type from useQuery
  if (isError) {
      let errorMessage = 'Unknown error';
      const errorObj = error as any; // Cast to any for instanceof check
      if (errorObj instanceof ApiError) {
          errorMessage = `${errorObj.message}${errorObj.detail ? ` (${errorObj.detail})` : ''}`;
      } else if (errorObj instanceof Error) {
          errorMessage = errorObj.message;
      }
      return <div className="text-red-600 p-4">Error loading shape details: {errorMessage}</div>;
  }
  if (!shapeDetail) return <div className="p-4">Shape details not found.</div>;

  return (
    <div>
      <p><strong>Stencil:</strong> {shapeDetail.stencil_name} ({shapeDetail.stencil_path})</p>
      <p><strong>Shape ID:</strong> {shapeDetail.shape_id}</p>
      <p><strong>Dimensions:</strong> {shapeDetail.width?.toFixed(2) ?? 'N/A'} x {shapeDetail.height?.toFixed(2) ?? 'N/A'}</p>
      {shapeDetail.geometry && <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto max-h-40">Geometry: {JSON.stringify(shapeDetail.geometry, null, 2)}</pre>}
      {shapeDetail.properties && <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto max-h-40">Properties: {JSON.stringify(shapeDetail.properties, null, 2)}</pre>}
    </div>
  );
}


export default function HomePage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [selectedShapeId, setSelectedShapeId] = useState<number | null>(null);
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  const RESULTS_PER_PAGE = 12;

  const { data: searchData, isLoading, isError, error, isFetching } = useSearchShapes(
    debouncedSearchTerm,
    page,
    RESULTS_PER_PAGE,
    {
       enabled: debouncedSearchTerm.length > 0,
       placeholderData: (previousData) => previousData,
    }
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedSearchTerm]);

  const addFavoriteMutation = useAddFavorite({
    onSuccess: (data) => {
      toast.success("Favorite Added", {
         description: `${data.shape_name || data.stencil_path} added to favorites.`
      });
    },
    onError: (error) => {
       const apiError = error as ApiError; // Cast error
       toast.error("Error Adding Favorite", {
         description: apiError?.detail || apiError?.message || "Could not add favorite.",
       });
    },
  });

  const handleAddFavorite = useCallback((shape: ShapeSummary) => {
     const payload: AddFavoritePayload = {
       shape_id: shape.shape_id,
       stencil_path: shape.stencil_path,
     };
     addFavoriteMutation.mutate(payload);
  }, [addFavoriteMutation]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const totalPages = searchData ? Math.ceil(searchData.total / RESULTS_PER_PAGE) : 0;

  // Function to render the error message cleanly
  const renderErrorMessage = () => {
    const errorObj = error as any; // Cast to any for instanceof check
    if (errorObj instanceof ApiError) {
      return `${errorObj.message}${errorObj.detail ? `\nDetails: ${errorObj.detail}` : ''}`;
    } else if (errorObj instanceof Error) {
      return errorObj.message;
    }
    return 'An unknown error occurred';
  };


  return (
    <div className="container mx-auto p-4 md:p-6">
      <h1 className="text-3xl font-bold mb-6">Stencil Search</h1>
      <div className="mb-6">
        <Input
          type="search"
          placeholder="Search for shapes..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="max-w-md text-base"
        />
      </div>

      {(isLoading || (isFetching && debouncedSearchTerm.length > 0)) && (
        <div className="flex items-center justify-center py-10 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin mr-3" />
          <span>Loading results...</span>
        </div>
      )}

      {isError && !isLoading && (
        <div className="text-red-600 bg-red-50 border border-red-300 p-4 rounded-md my-4">
          <p className="font-semibold">Error fetching search results:</p>
          <pre className="mt-2 text-sm whitespace-pre-wrap">
            {renderErrorMessage()}
           </pre>
        </div>
      )}

      {searchData && searchData.results.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground mb-4">
            Showing results {(page - 1) * RESULTS_PER_PAGE + 1} - {Math.min(page * RESULTS_PER_PAGE, searchData.total)} of {searchData.total} for "{debouncedSearchTerm}"
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {searchData.results.map((shape) => (
              <Card key={shape.shape_id} className="flex flex-col">
                <CardHeader className="pb-2">
                  <DialogTrigger asChild onClick={() => setSelectedShapeId(shape.shape_id)}>
                     <CardTitle className="text-base font-medium truncate hover:text-primary cursor-pointer" title={shape.shape_name}>
                        {shape.shape_name}
                     </CardTitle>
                  </DialogTrigger>
                  <CardDescription className="text-xs truncate" title={shape.stencil_path}>
                    {shape.stencil_name || 'Unknown Stencil'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow flex flex-col justify-between">
                  <AspectRatio ratio={1 / 1} className="bg-muted rounded-md mb-3 flex items-center justify-center">
                     <Eye className="h-1/2 w-1/2 text-muted-foreground opacity-50" />
                  </AspectRatio>
                  <div className="flex justify-between items-center gap-2">
                    <DialogTrigger asChild onClick={() => setSelectedShapeId(shape.shape_id)}>
                       <Button variant="outline" size="sm" className="flex-grow">Details</Button>
                    </DialogTrigger>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleAddFavorite(shape)}
                      disabled={addFavoriteMutation.isPending} // Use isPending
                      title="Add to Favorites"
                    >
                      <Heart className={`h-4 w-4 ${addFavoriteMutation.isPending && addFavoriteMutation.variables?.shape_id === shape.shape_id ? 'animate-pulse text-red-500 fill-red-500' : 'text-muted-foreground hover:text-red-500'}`} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
             <div className="flex justify-center items-center space-x-2 mt-8">
                <Button variant="outline" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1 || isFetching}>Previous</Button>
                <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                <Button variant="outline" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages || isFetching}>Next</Button>
             </div>
          )}
        </>
      )}

       {searchData && searchData.total === 0 && !isLoading && debouncedSearchTerm.length > 0 && (
         <p className="text-center text-muted-foreground mt-8">No results found for "{debouncedSearchTerm}".</p>
       )}

       {!isLoading && debouncedSearchTerm.length === 0 && (
          <p className="text-center text-muted-foreground mt-8">Enter a search term above to find shapes.</p>
       )}

        <Dialog open={selectedShapeId !== null} onOpenChange={(open) => !open && setSelectedShapeId(null)}>
             <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                   <DialogTitle>Shape Details</DialogTitle>
                </DialogHeader>
                {selectedShapeId && <ShapeDetailView shapeId={selectedShapeId} />}
                <DialogFooter>
                   <Button variant="outline" onClick={() => setSelectedShapeId(null)}>Close</Button>
                </DialogFooter>
             </DialogContent>
        </Dialog>

    </div>
  );
}
