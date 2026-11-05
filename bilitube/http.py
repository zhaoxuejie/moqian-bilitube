"""B 站 HTTP 客户端：直连、限速、退避重试、风控统计。

设计要点：
- 默认直连（不走系统代理），避免账号异地风控
- 默认不携带 Cookie，只有显式传入 SESSDATA 时才带
- -352/-412 视为可重试，-403/-404 视为不可重试
- 连续请求中 -352 比例超过阈值时主动中断，保护账号与 IP
"""

from __future__ import annotations

import html
import re
import time
import zlib
from typing import Any, Callable

import httpx

BASE_URL = "https://api.bilibili.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
REFERER = "https://www.bilibili.com/"

RETRYABLE_CODES = (-352, -412)
NON_RETRYABLE_CODES = (-403, -404, -405)

DANMAKU_PATTERN = re.compile(r'<d p="[^"]*">([^<]*)</d>')


class BiliApiError(RuntimeError):
    """B 站接口错误；retryable 表示是否值得重试。"""

    def __init__(self, code: int, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.retryable = retryable


class BiliClient:
    """B 站接口封装。"""

    def __init__(
        self,
        *,
        rate_limit_rps: float = 1.5,
        timeout: float = 20.0,
        sessdata: str | None = None,
        max_attempts: int = 3,
        abort_threshold: float = 0.05,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        client: httpx.Client | None = None,
    ) -> None:
        self.rate_limit_rps = rate_limit_rps
        self.max_attempts = max_attempts
        self.abort_threshold = abort_threshold
        self._sleeper = sleeper
        self._clock = clock
        self._last_call: float | None = None
        self._sessdata = sessdata
        self._client = client or httpx.Client(
            timeout=timeout,
            headers=self._base_headers(),
        )
        self.stats: dict[str, int] = {"requests": 0, "ok": 0, "risk_control": 0, "errors": 0}

    # ---------- 基础设施 ----------

    def _base_headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Referer": REFERER}

    def headers(self) -> dict[str, str]:
        headers = self._base_headers()
        if self._sessdata:
            headers["Cookie"] = f"SESSDATA={self._sessdata}"
        return headers

    def _throttle(self) -> None:
        if self.rate_limit_rps <= 0:
            return
        interval = 1.0 / self.rate_limit_rps
        now = self._clock()
        if self._last_call is not None:
            wait = interval - (now - self._last_call)
            if wait > 0:
                self._sleeper(wait)
        self._last_call = self._clock()

    def _backoff(self, attempt: int) -> None:
        self._sleeper(min(2 ** attempt, 30))

    def _risk_ratio(self) -> float:
        if self.stats["requests"] == 0:
            return 0.0
        return self.stats["risk_control"] / self.stats["requests"]

    def _check_abort(self) -> None:
        if self.stats["requests"] >= 20 and self._risk_ratio() > self.abort_threshold:
            raise BiliApiError(
                -352,
                f"-352 比例 {self._risk_ratio():.1%} 超过阈值 {self.abort_threshold:.0%}，已暂停采集",
            )

    def _request(self, path: str, params: dict[str, Any], *, raw: bool = False) -> Any:
        url = f"{BASE_URL}{path}"
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            self._throttle()
            try:
                response = self._client.get(url, params=params, headers=self.headers())
            except httpx.HTTPError as exc:
                last_error = exc
                self.stats["errors"] += 1
                if attempt == self.max_attempts - 1:
                    break
                self._backoff(attempt)
                continue

            self.stats["requests"] += 1
            if response.status_code != 200:
                is_throttle = response.status_code in (412, 429)
                if is_throttle:
                    self.stats["risk_control"] += 1
                last_error = BiliApiError(
                    response.status_code,
                    f"HTTP {response.status_code}",
                    retryable=response.status_code >= 500 or is_throttle,
                )
                self.stats["errors"] += 1
                if attempt == self.max_attempts - 1:
                    break
                self._backoff(attempt)
                continue

            if raw:
                self.stats["ok"] += 1
                return response.content

            try:
                payload = response.json()
            except ValueError as exc:
                last_error = exc
                self.stats["errors"] += 1
                if attempt == self.max_attempts - 1:
                    break
                self._backoff(attempt)
                continue

            code = payload.get("code")
            if code == 0:
                self.stats["ok"] += 1
                return payload

            if code in RETRYABLE_CODES:
                self.stats["risk_control"] += 1
                self._check_abort()
                last_error = BiliApiError(code, payload.get("message", ""), retryable=True)
                if attempt == self.max_attempts - 1:
                    break
                self._backoff(attempt)
                continue

            raise BiliApiError(
                code,
                payload.get("message", ""),
                retryable=code not in NON_RETRYABLE_CODES,
            )

        assert last_error is not None
        if isinstance(last_error, BiliApiError):
            raise last_error
        raise BiliApiError(-1, f"网络请求失败: {last_error}")

    # ---------- 业务接口 ----------

    def search_videos(
        self,
        keyword: str,
        *,
        order: str = "stow",
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """关键词搜索。

        使用非 wbi 的旧版接口：实测 wbi 版在高频下会返回 v_voucher 风控挑战，
        旧版接口在同等频率下更稳定；两种接口返回字段一致。
        """
        last_error: BiliApiError | None = None
        for attempt in range(self.max_attempts):
            payload = self._request(
                "/x/web-interface/search/type",
                {
                    "search_type": "video",
                    "keyword": keyword,
                    "order": order,
                    "page": page,
                    "page_size": page_size,
                },
            )
            data = payload.get("data") or {}
            challenged = bool(data.get("v_voucher")) or "result" not in data
            if not challenged:
                return list(data.get("result") or [])

            # 风控挑战：code 仍是 0，但 data 里只有 v_voucher，必须显式识别
            self.stats["risk_control"] += 1
            self._check_abort()
            last_error = BiliApiError(
                -352,
                "搜索接口返回风控挑战（v_voucher），请降低频率或更换出口 IP",
                retryable=True,
            )
            if attempt < self.max_attempts - 1:
                self._backoff(attempt)

        raise last_error or BiliApiError(-352, "搜索接口持续返回风控挑战")

    def search_total(self, keyword: str) -> int:
        payload = self._request(
            "/x/web-interface/search/type",
            {"search_type": "video", "keyword": keyword, "page": 1},
        )
        return int((payload.get("data") or {}).get("numResults") or 0)

    def video_detail(self, bvid: str) -> dict[str, Any]:
        payload = self._request("/x/web-interface/view", {"bvid": bvid})
        return dict(payload.get("data") or {})

    def up_fans(self, mid: int) -> int | None:
        payload = self._request("/x/relation/stat", {"vmid": mid})
        data = payload.get("data") or {}
        return data.get("follower")

    def comments(self, aid: int, *, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        payload = self._request(
            "/x/v2/reply",
            {"type": 1, "oid": aid, "pn": page, "ps": page_size, "sort": 2},
        )
        data = payload.get("data") or {}
        return list(data.get("replies") or [])

    def danmaku(self, cid: int) -> list[str]:
        content = self._request("/x/v1/dm/list.so", {"oid": cid}, raw=True)
        try:
            xml = zlib.decompress(content, -zlib.MAX_WBITS).decode("utf-8", "replace")
        except zlib.error:
            xml = content.decode("utf-8", "replace")
        return [html.unescape(text) for text in DANMAKU_PATTERN.findall(xml)]

    def subtitles(self, bvid: str, cid: int) -> list[dict[str, Any]]:
        payload = self._request("/x/player/v2", {"bvid": bvid, "cid": cid})
        data = payload.get("data") or {}
        subtitle = data.get("subtitle") or {}
        return list(subtitle.get("subtitles") or [])

    def close(self) -> None:
        self._client.close()
