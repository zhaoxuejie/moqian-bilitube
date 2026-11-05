import type { Metadata } from "next";
import Link from "next/link";
import { ArrowIcon } from "@/components/icons";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: "隐私与免责 · BiliTube",
  description:
    "BiliTube 不收集个人信息：收藏只存在本地浏览器，详情页会连接 B 站官方播放器与图床。",
  alternates: { canonical: "/privacy/" },
};

const POINTS = [
  {
    title: "不收集个人信息",
    body: "本站没有账号、登录、表单和后端数据库。不采集姓名、手机号、邮箱等任何可识别身份的信息。",
  },
  {
    title: "收藏只存在你自己的浏览器里",
    body: "点「收藏」时，视频编号写进浏览器的 localStorage（键名 bilitube:favorites）。数据不会上传到任何服务器，也不跨设备同步；清除浏览器数据即彻底消失。",
  },
  {
    title: "访问时会连接 B 站",
    body: "详情页嵌入了 B 站官方播放器，封面图片直连 B 站图床（i0–i2.hdslb.com）。打开这些页面时，你的浏览器会向 bilibili.com 发起请求（包含 IP 地址、User-Agent），可能被 B 站记录，适用哔哩哔哩自己的隐私政策。",
  },
  {
    title: "没有统计与广告",
    body: "站内不加载任何第三方统计、广告或社交插件脚本。若未来启用访问统计，会在此写明统计方式与退出方法。",
  },
  {
    title: "内容版权",
    body: "站内视频的版权归各 UP 主与哔哩哔哩所有。本站只做索引、评分与文字评价，不转存视频、不二次分发。",
  },
  {
    title: "非官方项目",
    body: "本站为个人项目，与哔哩哔哩官方无任何关联，不代表其立场。评分与评价是相对排序，不是绝对结论。",
  },
];

export default function PrivacyPage() {
  return (
    <main className="shell page">
      <div className="crumbs">
        <Link href="/">精选</Link>
        <span className="sep">/</span>
        <span>隐私与免责</span>
      </div>

      <h1>隐私与免责</h1>
      <p className="page-lede">
        这是一个纯静态的精选站点：没有后端、没有账号、不收集个人信息。
        下面把「会碰到的数据」逐条列清楚，包括访问时会连接 B 站这件事。
      </p>

      <ol className="policy">
        {POINTS.map((point) => (
          <li key={point.title}>
            <h2>{point.title}</h2>
            <p>{point.body}</p>
          </li>
        ))}
      </ol>

      <section className="page-contact">
        <h2>反馈与联系方式</h2>
        {/* 渠道在 web/lib/site.ts 里配置；两个都为空时只保留一句说明 */}
        <p>
          发现误判、失效链接、想补充某个主题，或者你是 UP 主希望自己的视频被移除，
          都可以在 GitHub 上提 issue。这是本项目唯一的官方联系渠道。
          {SITE.repo || SITE.contact ? "" : "（渠道整理中，稍后补上。）"}
        </p>
        <div className="page-actions">
          {SITE.repo ? (
            <>
              <a
                className="btn"
                href={`${SITE.repo}/issues/new`}
                target="_blank"
                rel="noreferrer"
              >
                提交 Issue
                <ArrowIcon size={11} />
              </a>
              <a className="btn" href={SITE.repo} target="_blank" rel="noreferrer">
                GitHub 仓库
                <ArrowIcon size={11} />
              </a>
            </>
          ) : null}
          {SITE.contact ? (
            <a className="btn" href={`mailto:${SITE.contact}`}>
              {SITE.contact}
            </a>
          ) : null}
          <Link className="btn" href="/">
            回到精选
          </Link>
        </div>
      </section>

      <p className="page-meta">最后更新：{SITE.updatedAt}</p>
    </main>
  );
}
