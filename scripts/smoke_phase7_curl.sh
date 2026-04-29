#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   export BASE_URL="http://127.0.0.1:8000"
#   export TOKEN="<jwt>"
#   export RUN_KEY="<existing run key>"      # optional, if you want to skip create
#   export CAMPAIGN_ID="<campaign id>"       # optional
#   bash scripts/smoke_phase7_curl.sh

if [[ -z "${BASE_URL:-}" || -z "${TOKEN:-}" ]]; then
  echo "BASE_URL and TOKEN are required."
  exit 1
fi

echo "== 1) Create workflow run =="
curl -sS -X POST "$BASE_URL/api/v1/workflow/runs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
echo
echo

if [[ -n "${RUN_KEY:-}" ]]; then
  echo "== 2) Stream workflow run =="
  curl -N -sS "$BASE_URL/api/v1/workflow/runs/$RUN_KEY/stream" \
    -H "Authorization: Bearer $TOKEN"
  echo
  echo

  echo "== 3) Read workflow run details =="
  curl -sS "$BASE_URL/api/v1/workflow/runs/$RUN_KEY" \
    -H "Authorization: Bearer $TOKEN"
  echo
  echo
fi

echo "== 4) Save asset to library (canonical endpoint) =="
curl -sS -X POST "$BASE_URL/api/v1/assets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type":"video",
    "title":"Smoke Asset",
    "content_url":"https://example.com/video.mp4",
    "text_content":"Smoke test body",
    "status":"pending_review",
    "platforms_used":["twitter","linkedin"]
  }'
echo
echo

echo "== 5) List assets (canonical endpoint) =="
curl -sS "$BASE_URL/api/v1/assets?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN"
echo
echo

echo "== 6) List assets (legacy compatibility endpoint) =="
curl -sS "$BASE_URL/api/v1/assets/assets?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN"
echo
echo

if [[ -n "${CAMPAIGN_ID:-}" ]]; then
  echo "== 7) Trigger campaign run-now =="
  curl -sS -X POST "$BASE_URL/api/v1/campaigns/$CAMPAIGN_ID/run-now" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json"
  echo
  echo
fi

echo "Smoke script finished."
