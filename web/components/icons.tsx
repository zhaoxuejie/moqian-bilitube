export function SearchIcon({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      aria-hidden="true"
    >
      <circle cx="7" cy="7" r="4.6" />
      <path d="M10.6 10.6 14 14" strokeLinecap="round" />
    </svg>
  );
}

export function PlayIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
      <path d="M5.5 3.6 12 8l-6.5 4.4V3.6Z" fill="currentColor" />
    </svg>
  );
}

export function BookmarkIcon({ size = 13, filled = false }: { size?: number; filled?: boolean }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.3"
      aria-hidden="true"
    >
      <path d="M4 2.5h8v11L8 10.8l-4 2.7v-11Z" strokeLinejoin="round" />
    </svg>
  );
}

export function ArrowIcon({ size = 12 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      {/* 右上箭头：外链的通用语义 */}
      <path d="M4.6 11.4 11.4 4.6" strokeLinecap="round" />
      <path d="M5.9 4.6h5.5v5.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** UP 主标识：一个最简的人形轮廓，用在卡片底部和详情页 */
export function UserIcon({ size = 13 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      aria-hidden="true"
    >
      <circle cx="8" cy="5.6" r="2.6" />
      <path d="M3.2 13.2c.6-2.4 2.5-3.8 4.8-3.8s4.2 1.4 4.8 3.8" strokeLinecap="round" />
    </svg>
  );
}
/** 浅色模式下显示（点它切到深色） */
export function MoonIcon({ size = 15 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      aria-hidden="true"
    >
      <path
        d="M13.2 9.6A5.4 5.4 0 0 1 6.4 2.8a5.4 5.4 0 1 0 6.8 6.8Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** 深色模式下显示（点它切回浅色） */
export function SunIcon({ size = 15 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="2.9" />
      <path
        d="M8 1.6v1.4M8 13v1.4M1.6 8h1.4M13 8h1.4M3.5 3.5l1 1M11.5 11.5l1 1M12.5 3.5l-1 1M4.5 11.5l-1 1"
        strokeLinecap="round"
      />
    </svg>
  );
}
/** GitHub 标记（实心） */
export function GitHubIcon({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .3C5.4.3.1 5.6.1 12.2c0 5.3 3.4 9.7 8.2 11.3.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.5-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11 11 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.7-2.8 5.7-5.5 6 .4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6a12 12 0 0 0 8.2-11.3C23.9 5.6 18.6.3 12 .3Z" />
    </svg>
  );
}

/** 博客 / 个人站点 */
export function GlobeIcon({ size = 13 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6.2" />
      <path d="M1.8 8h12.4M8 1.8c3.2 3.4 3.2 9 0 12.4M8 1.8c-3.2 3.4-3.2 9 0 12.4" />
    </svg>
  );
}

/** 微信（双气泡轮廓） */
export function WeChatIcon({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M9.2 3.2c-4 0-7.2 2.6-7.2 5.9 0 1.9 1.1 3.5 2.9 4.6l-.7 2.1 2.4-1.2c.8.2 1.7.4 2.6.4h.6a4.9 4.9 0 0 1-.2-1.4c0-3.1 3-5.6 6.7-5.6h.5C16.1 5.1 13 3.2 9.2 3.2Zm-2.4 3c.5 0 .9.4.9.9s-.4.9-.9.9-.9-.4-.9-.9.4-.9.9-.9Zm4.9 0c.5 0 .9.4.9.9s-.4.9-.9.9-.9-.4-.9-.9.4-.9.9-.9Z" />
      <path d="M22 13.9c0-2.7-2.6-4.9-5.9-4.9s-5.9 2.2-5.9 4.9 2.6 4.9 5.9 4.9c.7 0 1.4-.1 2.1-.3l2 1-.6-1.8c1.5-.9 2.4-2.3 2.4-3.8Zm-7.9-1.1c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7Zm4 0c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7Z" />
    </svg>
  );
}