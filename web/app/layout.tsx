import type { Metadata, Viewport } from "next";
import Link from "next/link";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { loadMeta } from "@/lib/data";
import { SITE_DESCRIPTION, SITE_ORIGIN, SITE_TITLE } from "@/lib/site";
import { formatNumber } from "@/lib/types";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_ORIGIN),
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  applicationName: "BiliTube",
  keywords: ["B站", "AI 视频", "大模型", "LLM", "视频精选", "学习路线", "BiliTube"],
  authors: [{ name: "BiliTube" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "zh_CN",
    siteName: "BiliTube",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: "/",
    images: [
      {
        url: "/og.png",
        width: 1200,
        height: 630,
        alt: "BiliTube · 翻完 3,652 个 AI 视频，留下这 1,360 个",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: ["/og.png"],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f7f4" },
    { media: "(prefers-color-scheme: dark)", color: "#15181a" },
  ],
};

/** 首帧前套用用户选过的主题，避免刷新时闪一下白 */
const THEME_SCRIPT = `try{var t=localStorage.getItem("bilitube:theme");if(t==="light"||t==="dark"){document.documentElement.dataset.theme=t}}catch(e){}`;

/** 三条方法论：内容取自 previews-colorways 翠绿模板的「关于这份清单」，逐字一致 */
const METHOD_ITEMS = [
  {
    index: "01",
    title: "先筛选，再推荐",
    body: "从 3,652 条候选中，经过相关性与质量规则筛选。",
  },
  {
    index: "02",
    title: "看见内容价值",
    body: "结合互动信号、简介与弹幕，生成内容判断和观看理由。",
  },
  {
    index: "03",
    title: "找到适合你的",
    body: "了解适合人群与前置知识，再决定从哪一课开始。",
  },
];

/** 2026-11-04T18:35:05 → 2026.11.04 */
function shortDate(value: string | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10).replace(/-/g, ".");
}

function Header() {
  const meta = loadMeta();
  return (
    <header className="site-header">
      <div className="shell">
        <Link className="brand" href="/">
          <Logo size={32} />
          <span className="brand-name">BiliTube</span>
          <span className="brand-sub">AI 视频精选</span>
        </Link>
        <nav className="site-nav">
          <Link href="/" className="hide-sm">
            精选
          </Link>
          <Link href="/#topics" className="hide-sm">
            主题
          </Link>
          <a href="#method" className="hide-sm">
            方法
          </a>
          <ThemeToggle />
          <span className="count">{formatNumber(meta.videos)} 条 · 持续更新</span>
        </nav>
      </div>
    </header>
  );
}

function Method() {
  return (
    <section className="method" id="method">
      <div className="shell method-grid">
        <div>
          <p className="method-label">关于这份清单</p>
          <h2 className="method-title">
            让每一次观看，
            <br />
            都更有收获。
          </h2>
        </div>
        <div className="method-items">
          {METHOD_ITEMS.map((item) => (
            <div className="method-item" key={item.index}>
              <span>{item.index}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const meta = loadMeta();
  return (
    <>
      <Method />
      <footer className="site-footer">
        <div className="shell">
          {/* 与方法区共用同一套网格：320px + 3 等列，竖向轴线对齐 */}
          <div className="footer-grid">
            <div className="footer-brand">
              <p className="mark">
                <Logo size={18} />
                <span>BiliTube</span>
              </p>
              <p>
                把 B 站 AI 区的候选视频按分区、时长分组做分位归一，
                再由大模型读完弹幕与简介给出判断。
              </p>
            </div>

            <div className="footer-cols">
              <div>
                <h4>口径</h4>
                <p>候选 {formatNumber(meta.candidates)} 条</p>
                <p>精选 {formatNumber(meta.videos)} 条</p>
                <p>弹幕样本 {formatNumber(meta.danmaku_rows)} 条</p>
                <p>主题 {formatNumber(meta.topics)} 个</p>
              </div>
              <div>
                <h4>评分</h4>
                <p>互动 60% · 内容 40%</p>
                <p>分位在同分区、同时长段内计算</p>
                <p>是相对排序，不是绝对结论</p>
              </div>
              <div id="about">
                <h4>来源</h4>
                <p>数据来自 B 站公开接口</p>
                <p>个人项目，与哔哩哔哩无关联</p>
                <p>视频版权归 UP 主，本站不转存</p>
              </div>
            </div>
          </div>

          <div className="footer-base">
            <p>© 2026 BiliTube · 个人项目，与哔哩哔哩无关联</p>
            <p>
              <Link href="/privacy/">隐私与免责</Link>
              <span aria-hidden="true"> · </span>
              数据更新 {shortDate(meta.generated_at)}
            </p>
          </div>
        </div>
      </footer>
    </>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        {/* 同步脚本放在 body 最前面：解析到内容之前就套好主题 */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <Header />
        {children}
        <Footer />
      </body>
    </html>
  );
}
