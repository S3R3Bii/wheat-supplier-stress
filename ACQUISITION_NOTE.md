# Recorded rate-limit correction before source qualification

The original capture code and 49 exact requests were committed at `dd9b16e3d661e9fcf24cb0f6cc4496b72e66d82a` before cohort retrieval. The first Morocco 2018 request succeeded with seven records. The second request returned HTTP 429, explicitly asking for a three-second wait. The original response, error body, request times and hashes remain private and unchanged. Only the envelope count and rate-limit message were inspected; no source qualification or scenario score ran.

One explicit slower continuation honors that elapsed provider wait and waits at least ten seconds after each subsequent response before starting the next request. It copies the first successful capture byte-for-byte instead of fetching it again and preserves the original failed attempt separately. Another error or rate limit stops collection, with no repeated continuation, alternative credential, account, IP, endpoint or quota bypass.

The cohort, exact URLs, quantity/common-support gates, authored scenarios and development/later boundary are unchanged. This is a documented acquisition integration correction, not an untouched acquisition-plan claim. Source response count is not a completed data-quality or analysis result. No trade projection or measured scenario finding is public yet.
