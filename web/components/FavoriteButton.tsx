"use client";

import { useEffect, useState } from "react";
import { BookmarkIcon } from "@/components/icons";
import { FAVORITES_EVENT, readFavorites, toggleFavorite } from "@/lib/favorites";

export default function FavoriteButton({ bvid }: { bvid: string }) {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const sync = () => setActive(readFavorites().includes(bvid));
    sync();
    window.addEventListener(FAVORITES_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(FAVORITES_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [bvid]);

  return (
    <button
      className={`btn${active ? " active" : ""}`}
      onClick={() => setActive(toggleFavorite(bvid).includes(bvid))}
      aria-pressed={active}
      title="收藏只存在这台设备的浏览器里，未登录、不上传"
    >
      <BookmarkIcon filled={active} />
      {active ? "已收藏" : "收藏"}
    </button>
  );
}
