import { useId } from "react";

/**
 * 站点标记：圆角方块内镂空小电视，配两颗圆点眼睛。
 * 用 CSS 变量取色，跟随 :root 里的配色令牌，换肤不用改这个文件。
 */
export default function Logo({ size = 30 }: { size?: number }) {
  const silhouetteId = useId();

  return (
    <svg
      className="logo"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <mask id={silhouetteId} maskUnits="userSpaceOnUse" x="0" y="0" width="32" height="32">
          <rect width="32" height="32" fill="white" />
          <rect x="6.8" y="11.3" width="18.4" height="11.6" rx="3.1" fill="black" />
          <path
            d="M13.9 11.9 10.1 7.7M17.6 11.9 20.8 8.6M11.3 22.2v1.6m9.4-1.6v1.6"
            fill="none"
            stroke="black"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </mask>
      </defs>
      <rect
        width="32"
        height="32"
        rx="7"
        fill="var(--accent)"
        mask={`url(#${silhouetteId})`}
      />
      <circle cx="12.6" cy="17" r="1.3" fill="var(--accent)" />
      <circle cx="19.4" cy="17" r="1.3" fill="var(--accent)" />
    </svg>
  );
}
