"use client";

import { useState } from "react";
import { GitHubIcon, GlobeIcon, WeChatIcon } from "@/components/icons";
import { SITE } from "@/lib/site";

/**
 * 页脚联系方式：GitHub / 博客 / 公众号。
 * 公众号二维码用「悬停显示 + 点击切换」，触屏设备上点击同样可用。
 */
export default function SocialLinks() {
  const [qrOpen, setQrOpen] = useState(false);

  if (!SITE.repo && !SITE.blog && !SITE.wechatQr) return null;

  return (
    <div className="social">
      {SITE.repo ? (
        <a className="social-link" href={SITE.repo} target="_blank" rel="noreferrer">
          <GitHubIcon />
          GitHub
        </a>
      ) : null}

      {SITE.blog ? (
        <a className="social-link" href={SITE.blog} target="_blank" rel="noreferrer">
          <GlobeIcon />
          博客
        </a>
      ) : null}

      {SITE.wechatQr ? (
        <span
          className="social-wechat"
          onMouseEnter={() => setQrOpen(true)}
          onMouseLeave={() => setQrOpen(false)}
        >
          <button
            type="button"
            className="social-link"
            aria-expanded={qrOpen}
            onClick={() => setQrOpen((open) => !open)}
          >
            <WeChatIcon />
            公众号
          </button>
          {qrOpen ? (
            <span className="social-qr">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={SITE.wechatQr} alt="微信公众号二维码" width={132} height={132} />
              {SITE.wechatName ? <em>{SITE.wechatName}</em> : null}
            </span>
          ) : null}
        </span>
      ) : null}
    </div>
  );
}
