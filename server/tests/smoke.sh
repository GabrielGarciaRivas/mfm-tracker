#!/bin/sh
# Checks a running server: health page, access keys, sending and reading sightings.
# Usage: smoke.sh URL KEY1 KEY2
set -eu
URL="$1"; K1="$2"; K2="$3"
fail() { echo "FAIL: $*"; exit 1; }
curl -fsS "$URL/health" | grep -q "is running" || fail "health page"
code=$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/v1/status")
[ "$code" = 401 ] || fail "no key should give 401, got $code"
curl -fsS -H "Authorization: Bearer $K1" "$URL/api/v1/status" | grep -q '"seq"' || fail "status"
curl -fsS -H "Authorization: Bearer $K1" -H 'Content-Type: application/json' -X POST "$URL/api/v1/sightings" \
  -d '{"sightings":[{"uid":"t1","ts":"2026-10-17T20:00:00Z","item":"Topaz","price":40000,"seller":"Alice","map":"FM 1"}]}' \
  | grep -q '"seq": 1' || fail "send"
# the same listing from someone else: kept once, and it's now sold
curl -fsS -H "Authorization: Bearer $K2" -H 'Content-Type: application/json' -X POST "$URL/api/v1/sightings" \
  -d '{"sightings":[{"uid":"t2","ts":"2026-10-17T20:10:00Z","item":"Topaz","price":40000,"seller":"alice","map":"FM 1","sold":1,"sold_ts":"2026-10-17T20:10:00Z","last_seen":"2026-10-17T20:10:00Z"}]}' \
  | grep -q '"t2": "t1"' || fail "same listing"
out=$(curl -fsS -H "Authorization: Bearer $K2" "$URL/api/v1/sightings?since=0")
echo "$out" | grep -q '"sold": 1' || fail "read back: $out"
[ "$(echo "$out" | grep -o '"uid"' | wc -l)" = 1 ] || fail "stored twice: $out"
# megaphones: two reads of the same one; the surer read wins and it's stored once
NOW=$(date -u +%Y-%m-%dT%H:%M:00Z)
curl -fsS -H "Authorization: Bearer $K1" -H 'Content-Type: application/json' -X POST "$URL/api/v1/megaphones" \
  -d "{\"megaphones\":[{\"uid\":\"m1\",\"ts\":\"$NOW\",\"player\":\"Locki024\",\"channel\":\"1\",\"message\":\"S>Gloves Attack Scroll\",\"kind\":\"sell\",\"conf\":61}]}" >/dev/null
curl -fsS -H "Authorization: Bearer $K2" -H 'Content-Type: application/json' -X POST "$URL/api/v1/megaphones" \
  -d "{\"megaphones\":[{\"uid\":\"m2\",\"ts\":\"$NOW\",\"player\":\"Lock1024\",\"channel\":\"1\",\"message\":\"S>Gloves Attack Scroll\",\"kind\":\"sell\",\"conf\":88}]}" \
  | grep -q '"m2": "m1"' || fail "same megaphone"
out=$(curl -fsS -H "Authorization: Bearer $K1" "$URL/api/v1/megaphones?since=0&hours=2")
echo "$out" | grep -q '"player": "Lock1024"' || fail "best read: $out"
[ "$(echo "$out" | grep -o '"uid"' | wc -l)" = 1 ] || fail "megaphone stored twice: $out"
echo "OK"
