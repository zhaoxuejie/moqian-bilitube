import { SITE } from "@/lib/site";

/**
 * Cloudflare Web Analytics 的 beacon。
 *
 * 选择手动注入而不是控制台「自动注入」：Worker 响应不一定被边缘注入，
 * 手动插能确定生效，也避免和自动注入重复计数。
 *
 * 该脚本不种 cookie、不做跨站追踪，只上报一次页面浏览的聚合数据，
 * 说明见隐私与免责页。
 */
export default function Analytics() {
  if (!SITE.analyticsToken) return null;

  return (
    <script
      type="module"
      defer
      src="https://static.cloudflareinsights.com/beacon.min.js"
      data-cf-beacon={JSON.stringify({ token: SITE.analyticsToken })}
    />
  );
}
