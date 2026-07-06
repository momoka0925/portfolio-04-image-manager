export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string;
}

export interface ImageMeta {
  id: number;
  original_filename: string;
  content_type: string;
  size: number;
  width: number | null;
  height: number | null;
  sha256: string;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED";
  has_thumbnail: boolean;
  created_at: string;
}

export interface ImagePage {
  items: ImageMeta[];
  total: number;
  page: number;
  limit: number;
}
