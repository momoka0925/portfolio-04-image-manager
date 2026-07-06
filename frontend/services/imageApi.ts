import { API_BASE_URL } from "@/lib/config";
import type { ApiResponse, ImageMeta, ImagePage } from "@/types";

async function parse<T>(res: Response): Promise<T> {
  const body = (await res.json()) as ApiResponse<T>;
  if (!res.ok || !body.success) {
    throw new Error(body.message || `エラー (${res.status})`);
  }
  return body.data as T;
}

export const imageApi = {
  list: (page = 1, limit = 24, sort = "created_at", order = "desc") =>
    fetch(
      `${API_BASE_URL}/images?page=${page}&limit=${limit}&sort=${sort}&order=${order}`,
    ).then((r) => parse<ImagePage>(r)),

  // アップロードは進捗取得のため XMLHttpRequest を使う
  upload: (
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<ImageMeta> =>
    new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/images`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };
      xhr.onload = () => {
        try {
          const body = JSON.parse(xhr.responseText) as ApiResponse<ImageMeta>;
          if (xhr.status >= 200 && xhr.status < 300 && body.success) {
            resolve(body.data as ImageMeta);
          } else {
            reject(new Error(body.message || `エラー (${xhr.status})`));
          }
        } catch {
          reject(new Error("レスポンスの解析に失敗しました"));
        }
      };
      xhr.onerror = () => reject(new Error("サーバーに接続できませんでした"));
      xhr.send(form);
    }),

  remove: (id: number) =>
    fetch(`${API_BASE_URL}/images/${id}`, { method: "DELETE" }).then((r) =>
      parse<null>(r),
    ),

  thumbnailUrl: (id: number) => `${API_BASE_URL}/images/${id}/thumbnail`,
  fileUrl: (id: number) => `${API_BASE_URL}/images/${id}/file`,
};
