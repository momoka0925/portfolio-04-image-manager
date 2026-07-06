"use client";

import { imageApi } from "@/services/imageApi";
import type { ImageMeta } from "@/types";

interface ImageCardProps {
  image: ImageMeta;
  onDelete: (id: number) => void;
}

const STATUS_LABEL: Record<ImageMeta["status"], string> = {
  PENDING: "生成待ち",
  PROCESSING: "生成中...",
  READY: "完了",
  FAILED: "エラー",
};

export function ImageCard({ image, onDelete }: ImageCardProps) {
  return (
    <div className="group relative overflow-hidden rounded-lg border border-gray-200 bg-white">
      <a href={imageApi.fileUrl(image.id)} target="_blank" rel="noopener noreferrer">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageApi.thumbnailUrl(image.id)}
          alt={image.original_filename}
          className="aspect-square w-full object-cover"
        />
      </a>
      <div className="p-2">
        <p className="truncate text-xs font-medium text-gray-800">{image.original_filename}</p>
        <div className="mt-1 flex items-center justify-between text-[10px] text-gray-500">
          <span>
            {image.width}×{image.height} ・ {(image.size / 1024).toFixed(0)}KB
          </span>
          <span
            className={
              image.status === "READY"
                ? "text-green-600"
                : image.status === "FAILED"
                  ? "text-red-600"
                  : "text-amber-600"
            }
          >
            {STATUS_LABEL[image.status]}
          </span>
        </div>
      </div>
      <button
        onClick={() => onDelete(image.id)}
        className="absolute right-1 top-1 rounded bg-black/50 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100"
      >
        削除
      </button>
    </div>
  );
}
