"use client";

import { useCallback, useEffect, useState } from "react";

import { imageApi } from "@/services/imageApi";
import type { ImageMeta } from "@/types";

import { ImageCard } from "./ImageCard";
import { Uploader } from "./Uploader";

export function Gallery() {
  const [images, setImages] = useState<ImageMeta[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const page = await imageApi.list();
      setImages(page.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "読み込みに失敗しました");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  // サムネイル生成中の画像があれば、状態が確定するまで数秒ごとに再取得する
  useEffect(() => {
    const pending = images.some((i) => i.status === "PENDING" || i.status === "PROCESSING");
    if (!pending) return;
    const timer = setTimeout(() => void load(), 2000);
    return () => clearTimeout(timer);
  }, [images, load]);

  const handleDelete = async (id: number) => {
    await imageApi.remove(id);
    await load();
  };

  return (
    <div className="space-y-4">
      <Uploader onUploaded={load} />

      {error && (
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {images.length === 0 ? (
        <p className="py-10 text-center text-sm text-gray-500">
          まだ画像がありません。上のエリアからアップロードしてください。
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {images.map((img) => (
            <ImageCard key={img.id} image={img} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
