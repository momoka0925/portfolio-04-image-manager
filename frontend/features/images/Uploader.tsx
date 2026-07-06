"use client";

import { useRef, useState } from "react";

import { imageApi } from "@/services/imageApi";

interface UploaderProps {
  onUploaded: () => void;
}

export function Uploader({ onUploaded }: UploaderProps) {
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const uploadFiles = async (files: FileList | File[]) => {
    setError(null);
    for (const file of Array.from(files)) {
      try {
        setProgress(0);
        await imageApi.upload(file, setProgress);
      } catch (e) {
        setError(e instanceof Error ? e.message : "アップロードに失敗しました");
      }
    }
    setProgress(null);
    onUploaded();
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files.length) void uploadFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"
        }`}
      >
        <p className="text-sm text-gray-600">
          画像をドラッグ&ドロップ、またはクリックして選択
        </p>
        <p className="mt-1 text-xs text-gray-400">PNG / JPEG / WebP / GIF（最大10MB）</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) void uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {progress !== null && (
        <div className="mt-2 h-2 w-full overflow-hidden rounded bg-gray-200">
          <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
