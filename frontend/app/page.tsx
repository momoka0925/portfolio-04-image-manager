import { Gallery } from "@/features/images/Gallery";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Image Manager</h1>
        <p className="mt-1 text-sm text-gray-500">
          画像アップロード・サムネイル自動生成・重複検知（FastAPI + Next.js）
        </p>
      </header>
      <Gallery />
    </main>
  );
}
