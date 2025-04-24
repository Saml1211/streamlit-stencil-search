import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { type } from 'os';

// ---------- API Base URL ----------
// Ensure this matches the running backend server address
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5100';

// ---------- Error Handling ----------
export class ApiError extends Error { // Added export
  status: number;
  statusText: string;
  detail?: string; // From FastAPI HTTPException

  constructor(message: string, status: number, statusText: string, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.detail = detail;
  }
}

async function handleApiResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail: string | undefined;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || JSON.stringify(errorJson);
    } catch (e) {
      // If response is not JSON, use text
      try {
        errorDetail = await res.text();
      } catch (textError) {
        errorDetail = "Could not parse error response body.";
      }
    }
    throw new ApiError(
      `API request failed: ${res.status} ${res.statusText}`,
      res.status,
      res.statusText,
      errorDetail
    );
  }
  // Handle 204 No Content specifically
  if (res.status === 204) {
     return Promise.resolve(null as T); // Or resolve with a specific indicator if needed
  }
  // Otherwise, parse JSON
  try {
     return await res.json() as Promise<T>;
  } catch (e) {
      // Handle cases where response is OK but not valid JSON (shouldn't happen with FastAPI usually)
      throw new ApiError(
          `API request succeeded (${res.status}) but failed to parse JSON response.`,
          res.status,
          res.statusText,
          `JSON Parse Error: ${e instanceof Error ? e.message : String(e)}`
      );
  }
}


// ---------- Backend Types (Mirrored from main.py Pydantic models) ----------

export interface ShapeSummary {
  shape_id: number;
  shape_name: string;
  stencil_name: string;
  stencil_path: string;
  // Optional fields from FTS search result
  rank?: number;
  snippet?: string;
}

export interface SearchResponse {
  results: ShapeSummary[];
  total: number;
  page: number;
  size: number;
}

export interface StencilSummary {
  path: string;
  name: string;
  extension: string;
  shape_count: number;
  file_size?: number | null;
  last_modified?: string | null;
}

export interface StencilShapeSummary {
  shape_id: number; // Include ID for linking/selection
  name: string;
  width?: number | null;
  height?: number | null;
}

export interface StencilDetail extends StencilSummary {
  shapes: StencilShapeSummary[];
  last_scan?: string | null;
}

export interface ShapeDetail extends ShapeSummary {
  width?: number | null;
  height?: number | null;
  geometry?: any | null; // Keep as 'any' for flexibility
  properties?: Record<string, any> | null; // Dictionary
}

export interface FavoriteItem {
  id: number;
  item_type: 'stencil' | 'shape';
  stencil_path: string;
  shape_id?: number | null;
  added_at: string;
  stencil_name?: string | null; // From JOIN
  shape_name?: string | null;   // From JOIN
}

export interface CollectionShapeSummary {
  shape_id: number;
  shape_name: string;
  stencil_path: string;
  stencil_name?: string | null;
}

export interface Collection {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
  shape_count?: number | null; // Populated in list/details view
  shapes?: CollectionShapeSummary[] | null; // Populated in detail view
}

export interface HealthStatus {
    api_status: string; // e.g., "ok"
    db_status: string; // e.g., "ok", "error"
    db_message?: string | null;
}

export interface IntegrationStatus {
    visio_status: string; // e.g., "connected", "disconnected", "error"
    message?: string | null;
    error_message?: string | null;
}

export interface DirectoryPath {
    id: number;
    path: string;
    name: string;
    is_active: boolean;
}

export interface DirectoryPath {
    id: number;
    path: string;
    name: string;
    is_active: boolean;
}

export interface ImportResponse {
    status: string;
    message?: string | null;
}

export interface CommandResponse {
    status: string;
    message?: string | null;
    result?: any | null;
}

// ---------- Payload Types for Mutations ----------

export interface AddFavoritePayload {
  stencil_path: string;
  shape_id?: number | null;
}

export interface CreateCollectionPayload {
    name: string;
}

export interface UpdateCollectionPayload {
    name?: string | null;
    add_shape_ids?: number[] | null;
    remove_shape_ids?: number[] | null;
}

export interface ImportPayload {
  type: 'text' | 'image';
  content: string;
  metadata?: {
    source_url?: string | null;
    capture_time?: string | null;
    user_options?: Record<string, any> | null;
  } | null;
}

export interface CommandPayload {
    command: string;
    params?: Record<string, any> | null;
}

export interface DirectoryPathPayload {
    path: string;
    name?: string;
}


// ---------- React Query Hook Implementations ----------

const STALE_TIME_DEFAULT = 1000 * 60 * 5; // 5 minutes
const STALE_TIME_SHORT = 1000 * 30; // 30 seconds (for status)

// --- Search ---
export function useSearchShapes(
  query: string,
  page: number = 1,
  size: number = 20,
  options?: Omit<UseQueryOptions<SearchResponse, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SearchResponse, ApiError>({
    queryKey: ['search', query, page, size],
    queryFn: async () => {
      const url = new URL(`${API_BASE}/search`);
      url.searchParams.append('q', query);
      url.searchParams.append('page', String(page));
      url.searchParams.append('size', String(size));
      const res = await fetch(url.toString());
      return handleApiResponse<SearchResponse>(res);
    },
    staleTime: STALE_TIME_DEFAULT,
    enabled: !!query && query.length > 0, // Only enable if query is not empty
    placeholderData: (previousData) => previousData, // Keep previous data while fetching new page
    ...options,
  });
}

// --- Stencils ---
export function useStencils(
  options?: Omit<UseQueryOptions<StencilSummary[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StencilSummary[], ApiError>({
    queryKey: ['stencils'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/stencils`);
      return handleApiResponse<StencilSummary[]>(res);
    },
    staleTime: STALE_TIME_DEFAULT,
    ...options,
  });
}

export function useStencilDetail(
  stencilPath: string | null | undefined, // Accept null/undefined to disable query
  options?: Omit<UseQueryOptions<StencilDetail, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StencilDetail, ApiError>({
    // Use path directly in query key after encoding
    queryKey: ['stencilDetail', stencilPath ? encodeURIComponent(stencilPath) : ''],
    queryFn: async () => {
      if (!stencilPath) throw new Error("Stencil path is required"); // Should not happen if enabled is false
      const encodedPath = encodeURIComponent(stencilPath);
      const res = await fetch(`${API_BASE}/stencils/${encodedPath}`);
      return handleApiResponse<StencilDetail>(res);
    },
    enabled: !!stencilPath, // Only run query if stencilPath is provided
    staleTime: STALE_TIME_DEFAULT,
    ...options,
  });
}

// --- Shapes ---
export function useShapeDetail(
  shapeId: number | null | undefined, // Accept null/undefined to disable query
  options?: Omit<UseQueryOptions<ShapeDetail, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ShapeDetail, ApiError>({
    queryKey: ['shapeDetail', shapeId],
    queryFn: async () => {
      if (shapeId === null || shapeId === undefined) throw new Error("Shape ID is required");
      const res = await fetch(`${API_BASE}/shapes/${shapeId}`);
      return handleApiResponse<ShapeDetail>(res);
    },
    enabled: shapeId !== null && shapeId !== undefined, // Only run query if shapeId is provided
    staleTime: STALE_TIME_DEFAULT,
    ...options,
  });
}


// --- Favorites ---
export function useFavorites(
   options?: Omit<UseQueryOptions<FavoriteItem[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<FavoriteItem[], ApiError>({
    queryKey: ['favorites'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/favorites`);
      return handleApiResponse<FavoriteItem[]>(res);
    },
     staleTime: STALE_TIME_DEFAULT,
     ...options,
  });
}

export function useAddFavorite(
  options?: Omit<UseMutationOptions<FavoriteItem, ApiError, AddFavoritePayload>, 'mutationFn'>
) {
  const queryClient = useQueryClient();
  return useMutation<FavoriteItem, ApiError, AddFavoritePayload>({
    mutationFn: async (payload) => {
      const res = await fetch(`${API_BASE}/favorites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      // Backend returns 201 Created with the new favorite item
      return handleApiResponse<FavoriteItem>(res);
    },
    onSuccess: () => {
      // Invalidate the favorites list to refetch
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
    ...options,
  });
}

export function useRemoveFavorite(
  options?: Omit<UseMutationOptions<void, ApiError, number /* fav_id */>, 'mutationFn'>
) {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, number>({
    mutationFn: async (favId) => {
      const res = await fetch(`${API_BASE}/favorites/${favId}`, {
        method: 'DELETE',
      });
      // Expect 204 No Content on success
      return handleApiResponse<void>(res);
    },
    onSuccess: () => {
      // Invalidate the favorites list to refetch
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
    ...options,
  });
}


// --- Collections ---
export function useCollections(
   options?: Omit<UseQueryOptions<Collection[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Collection[], ApiError>({
    queryKey: ['collections'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/collections`);
      // Note: Backend DB logic for collections might be incomplete
      return handleApiResponse<Collection[]>(res);
    },
     staleTime: STALE_TIME_DEFAULT,
     ...options,
  });
}

export function useCreateCollection(
  options?: Omit<UseMutationOptions<Collection, ApiError, CreateCollectionPayload>, 'mutationFn'>
) {
   const queryClient = useQueryClient();
   return useMutation<Collection, ApiError, CreateCollectionPayload>({
      mutationFn: async (payload) => {
         const res = await fetch(`${API_BASE}/collections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
         });
         // Note: Backend DB logic for collections might be incomplete
         return handleApiResponse<Collection>(res);
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['collections'] });
      },
      ...options,
   });
}

export function useCollectionDetails(
  collectionId: number | null | undefined,
  options?: Omit<UseQueryOptions<Collection, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Collection, ApiError>({
    queryKey: ['collectionDetail', collectionId],
    queryFn: async () => {
       if (collectionId === null || collectionId === undefined) throw new Error("Collection ID is required");
       const res = await fetch(`${API_BASE}/collections/${collectionId}`);
        // Note: Backend DB logic for collections might be incomplete
       return handleApiResponse<Collection>(res);
    },
    enabled: collectionId !== null && collectionId !== undefined,
    staleTime: STALE_TIME_DEFAULT,
    ...options,
  });
}

export function useUpdateCollection(
  options?: Omit<UseMutationOptions<Collection, ApiError, { id: number; payload: UpdateCollectionPayload }>, 'mutationFn'>
) {
   const queryClient = useQueryClient();
   return useMutation<Collection, ApiError, { id: number; payload: UpdateCollectionPayload }>({
      mutationFn: async ({ id, payload }) => {
         const res = await fetch(`${API_BASE}/collections/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
         });
          // Note: Backend DB logic for collections might be incomplete
         return handleApiResponse<Collection>(res);
      },
      onSuccess: (data, variables) => {
        queryClient.invalidateQueries({ queryKey: ['collections'] });
        queryClient.invalidateQueries({ queryKey: ['collectionDetail', variables.id] });
      },
      ...options,
   });
}


export function useDeleteCollection(
  options?: Omit<UseMutationOptions<void, ApiError, number /* collectionId */>, 'mutationFn'>
) {
   const queryClient = useQueryClient();
   return useMutation<void, ApiError, number>({
      mutationFn: async (collectionId) => {
         const res = await fetch(`${API_BASE}/collections/${collectionId}`, {
            method: 'DELETE',
         });
          // Note: Backend DB logic for collections might be incomplete
         return handleApiResponse<void>(res); // Expect 204
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['collections'] });
        // Also invalidate specific detail if cached? Maybe not necessary after delete.
      },
      ...options,
   });
}


// --- Health & Integration Status ---
export function useHealthStatus(
   options?: Omit<UseQueryOptions<HealthStatus, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<HealthStatus, ApiError>({
    queryKey: ['healthStatus'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`);
      return handleApiResponse<HealthStatus>(res);
    },
    staleTime: STALE_TIME_SHORT, // Check health more often
    refetchInterval: 15000, // Refetch every 15 seconds
    ...options,
  });
}

export function useIntegrationStatus(
   options?: Omit<UseQueryOptions<IntegrationStatus, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<IntegrationStatus, ApiError>({
    queryKey: ['integrationStatus'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/integration/status`);
      return handleApiResponse<IntegrationStatus>(res);
    },
     staleTime: STALE_TIME_SHORT, // Check status more often
     refetchInterval: 5000, // Refetch every 5 seconds
    ...options,
  });
}

// --- Import ---
export function useImportContent(
   options?: Omit<UseMutationOptions<ImportResponse, ApiError, ImportPayload>, 'mutationFn'>
) {
  return useMutation<ImportResponse, ApiError, ImportPayload>({
    mutationFn: async (payload: ImportPayload) => {
      const res = await fetch(`${API_BASE}/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return handleApiResponse<ImportResponse>(res);
    },
     ...options,
 });
}

// --- Directory Paths ---
export function useDirectoryPaths(
 options?: Omit<UseQueryOptions<DirectoryPath[], ApiError>, 'queryKey' | 'queryFn'>
) {
 return useQuery<DirectoryPath[], ApiError>({
     queryKey: ['directoryPaths'],
     queryFn: async () => {
         const res = await fetch(`${API_BASE}/directories`);
         return handleApiResponse<DirectoryPath[]>(res);
     },
     staleTime: STALE_TIME_DEFAULT,
     ...options,
 });
}

export function useActiveDirectory(
 options?: Omit<UseQueryOptions<DirectoryPath | null, ApiError>, 'queryKey' | 'queryFn'>
) {
 return useQuery<DirectoryPath | null, ApiError>({
     queryKey: ['activeDirectory'],
     queryFn: async () => {
         const res = await fetch(`${API_BASE}/directories/active`);
         return handleApiResponse<DirectoryPath | null>(res);
     },
     staleTime: STALE_TIME_SHORT, // Check more frequently
     ...options,
 });
}

export function useAddDirectory(
 options?: Omit<UseMutationOptions<DirectoryPath, ApiError, DirectoryPathPayload>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<DirectoryPath, ApiError, DirectoryPathPayload>({
     mutationFn: async (payload) => {
         const res = await fetch(`${API_BASE}/directories`, {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify(payload),
         });
         return handleApiResponse<DirectoryPath>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}

export function useSetActiveDirectory(
 options?: Omit<UseMutationOptions<DirectoryPath, ApiError, number>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<DirectoryPath, ApiError, number>({
     mutationFn: async (directoryId) => {
         const res = await fetch(`${API_BASE}/directories/${directoryId}/activate`, {
             method: 'PUT',
         });
         return handleApiResponse<DirectoryPath>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}

export function useRemoveDirectory(
 options?: Omit<UseMutationOptions<void, ApiError, number>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<void, ApiError, number>({
     mutationFn: async (directoryId) => {
         const res = await fetch(`${API_BASE}/directories/${directoryId}`, {
             method: 'DELETE',
         });
         return handleApiResponse<void>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}

// --- Directory Paths ---
export function useDirectoryPaths(
 options?: Omit<UseQueryOptions<DirectoryPath[], ApiError>, 'queryKey' | 'queryFn'>
) {
 return useQuery<DirectoryPath[], ApiError>({
     queryKey: ['directoryPaths'],
     queryFn: async () => {
         const res = await fetch(`${API_BASE}/directories`);
         return handleApiResponse<DirectoryPath[]>(res);
     },
     staleTime: STALE_TIME_DEFAULT,
     ...options,
 });
}

export function useActiveDirectory(
 options?: Omit<UseQueryOptions<DirectoryPath | null, ApiError>, 'queryKey' | 'queryFn'>
) {
 return useQuery<DirectoryPath | null, ApiError>({
     queryKey: ['activeDirectory'],
     queryFn: async () => {
         const res = await fetch(`${API_BASE}/directories/active`);
         return handleApiResponse<DirectoryPath | null>(res);
     },
     staleTime: STALE_TIME_SHORT, // Check more frequently
     ...options,
 });
}

export function useAddDirectory(
 options?: Omit<UseMutationOptions<DirectoryPath, ApiError, DirectoryPathPayload>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<DirectoryPath, ApiError, DirectoryPathPayload>({
     mutationFn: async (payload) => {
         const res = await fetch(`${API_BASE}/directories`, {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify(payload),
         });
         return handleApiResponse<DirectoryPath>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}

export function useSetActiveDirectory(
 options?: Omit<UseMutationOptions<DirectoryPath, ApiError, number>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<DirectoryPath, ApiError, number>({
     mutationFn: async (directoryId) => {
         const res = await fetch(`${API_BASE}/directories/${directoryId}/activate`, {
             method: 'PUT',
         });
         return handleApiResponse<DirectoryPath>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}

export function useRemoveDirectory(
 options?: Omit<UseMutationOptions<void, ApiError, number>, 'mutationFn'>
) {
 const queryClient = useQueryClient();
 return useMutation<void, ApiError, number>({
     mutationFn: async (directoryId) => {
         const res = await fetch(`${API_BASE}/directories/${directoryId}`, {
             method: 'DELETE',
         });
         return handleApiResponse<void>(res);
     },
     onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['directoryPaths'] });
         queryClient.invalidateQueries({ queryKey: ['activeDirectory'] });
     },
     ...options,
 });
}


// --- Backend Commands ---
export function useTriggerCommand(
   options?: Omit<UseMutationOptions<CommandResponse, ApiError, CommandPayload>, 'mutationFn'>
) {
    return useMutation<CommandResponse, ApiError, CommandPayload>({
        mutationFn: async (payload) => {
           const res = await fetch(`${API_BASE}/integration/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
           });
           return handleApiResponse<CommandResponse>(res);
        },
        ...options,
    });
}