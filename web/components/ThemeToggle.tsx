"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "@/components/icons";

const KEY = "bilitube:theme";
type Theme = "light" | "dark";

/** 读取「当前实际生效」的主题：显式选择优先，否则跟随系统。 */
function resolveTheme(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTheme(resolveTheme());
    setReady(true);
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // 隐私模式下存不进去也无妨，刷新后回退到系统偏好
    }
    setTheme(next);
  };

  const label = theme === "dark" ? "切换到浅色模式" : "切换到深色模式";

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={label}
      title={label}
      suppressHydrationWarning
    >
      {ready && theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
