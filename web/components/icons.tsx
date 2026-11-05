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