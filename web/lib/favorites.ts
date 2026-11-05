/**
 * 收藏存在浏览器本地（localStorage），不上传、不登录。
 * 写完之后派发一个自定义事件，让同页面的其他组件能立刻同步。
 */
const KEY = "bilitube:favorites";
export const FAVORITES_EVENT = "bilitube:favorites-changed";

export function readFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(value) ? (value as string[]) : [];
  } catch {
    return [];
  }
}

export function writeFavorites(list: string[]): void {
  window.localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event(FAVORITES_EVENT));
}

export function toggleFavorite(bvid: string): string[] {
  const list = readFavorites();
  const next = list.includes(bvid) ? list.filter((item) => item !== bvid) : [...list, bvid];
  writeFavorites(next);
  return next;
}
