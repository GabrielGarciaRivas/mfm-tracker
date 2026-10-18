#!/bin/sh
# Checks a running server: health page, accounts and sign-in, sending and reading
# sightings and megaphones.  Usage: smoke.sh URL USER1 PASSWORD1 USER2 PASSWORD2
set -eu
URL="$1"; U1="$2"; P1="$3"; U2="$4"; P2="$5"
fail() { echo "FAIL: $*"; exit 1; }
j() { curl -fsS -H 'Content-Type: application/json' "$@"; }
curl -fsS "$URL/health" | grep -q "is running" || fail "health page"
code=$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/v1/status")
[ "$code" = 401 ] || fail "no sign-in should give 401, got $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$URL/api/v1/login" -d "{\"username\":\"$U1\",\"password\":\"wrong\"}")
[ "$code" = 401 ] || fail "wrong password should give 401, got $code"
T1=$(j -X POST "$URL/api/v1/login" -d "{\"username\":\"$U1\",\"password\":\"$P1\"}" | sed 's/.*"token": "\([^"]*\)".*/\1/')
T2=$(j -X POST "$URL/api/v1/login" -d "{\"username\":\"$U2\",\"password\":\"$P2\"}" | sed 's/.*"token": "\([^"]*\)".*/\1/')
j -H "Authorization: Bearer $T1" "$URL/api/v1/status" | grep -q "\"name\": \"$U1\"" || fail "status"
j -H "Authorization: Bearer $T1" -X POST "$URL/api/v1/sightings" \
  -d '{"sightings":[{"uid":"t1","ts":"2026-10-17T20:00:00Z","item":"Topaz","price":40000,"seller":"Alice","map":"FM 1"}]}' \
  | grep -q '"seq": 1' || fail "send"
# the same listing from someone else: kept once, and it's now sold
j -H "Authorization: Bearer $T2" -X POST "$URL/api/v1/sightings" \
  -d '{"sightings":[{"uid":"t2","ts":"2026-10-17T20:10:00Z","item":"Topaz","price":40000,"seller":"alice","map":"FM 1","sold":1,"sold_ts":"2026-10-17T20:10:00Z","last_seen":"2026-10-17T20:10:00Z"}]}' \
  | grep -q '"t2": "t1"' || fail "same listing"
out=$(j -H "Authorization: Bearer $T2" "$URL/api/v1/sightings?since=0")
echo "$out" | grep -q '"sold": 1' || fail "read back: $out"
echo "$out" | grep -q "\"by\": \"$U1\"" || fail "who sent it: $out"
[ "$(echo "$out" | grep -o '"uid"' | wc -l)" = 1 ] || fail "stored twice: $out"
# megaphones: two reads of the same one; the surer read wins and it's stored once
NOW=$(date -u +%Y-%m-%dT%H:%M:00Z)
j -H "Authorization: Bearer $T1" -X POST "$URL/api/v1/megaphones" \
  -d "{\"megaphones\":[{\"uid\":\"m1\",\"ts\":\"$NOW\",\"player\":\"Locki024\",\"channel\":\"1\",\"message\":\"S>Gloves Attack Scroll\",\"kind\":\"sell\",\"conf\":61}]}" >/dev/null
j -H "Authorization: Bearer $T2" -X POST "$URL/api/v1/megaphones" \
  -d "{\"megaphones\":[{\"uid\":\"m2\",\"ts\":\"$NOW\",\"player\":\"Lock1024\",\"channel\":\"1\",\"message\":\"S>Gloves Attack Scroll\",\"kind\":\"sell\",\"conf\":88}]}" \
  | grep -q '"m2": "m1"' || fail "same megaphone"
out=$(j -H "Authorization: Bearer $T1" "$URL/api/v1/megaphones?since=0&hours=2")
echo "$out" | grep -q '"player": "Lock1024"' || fail "best read: $out"
[ "$(echo "$out" | grep -o '"uid"' | wc -l)" = 1 ] || fail "megaphone stored twice: $out"
# nicknames: one player teaches one, the other reads it; the newest change wins
j -H "Authorization: Bearer $T1" -X POST "$URL/api/v1/nicknames" \
  -d "{\"nicknames\":[{\"key\":\"kumbis\",\"item\":\"Kumbi Throwing-Stars\",\"updated\":\"$NOW\"}]}" >/dev/null
j -H "Authorization: Bearer $T2" -X POST "$URL/api/v1/nicknames" \
  -d '{"nicknames":[{"key":"kumbis","item":"Old Guess","updated":"2020-01-01T00:00:00Z"}]}' >/dev/null
out=$(j -H "Authorization: Bearer $T2" "$URL/api/v1/nicknames?since=0")
echo "$out" | grep -q '"item": "Kumbi Throwing-Stars"' || fail "nickname: $out"
echo "$out" | grep -q "\"by\": \"$U1\"" || fail "who taught it: $out"
# "not an item" is a nickname too
j -H "Authorization: Bearer $T1" -X POST "$URL/api/v1/nicknames" \
  -d "{\"nicknames\":[{\"key\":\"slime set\",\"item\":\"\",\"updated\":\"$NOW\"}]}" >/dev/null
out=$(j -H "Authorization: Bearer $T2" "$URL/api/v1/nicknames?since=0")
echo "$out" | grep -q '"slime set"' || fail "not-an-item not stored: $out"
# what was purged is listed for the apps
j -H "Authorization: Bearer $T2" "$URL/api/v1/purges?since=0" | grep -q '"purges"' || fail "purges"
# signing out ends the token
j -H "Authorization: Bearer $T2" -X POST "$URL/api/v1/logout" -d '{}' >/dev/null
code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T2" "$URL/api/v1/status")
[ "$code" = 401 ] || fail "signed-out token still works ($code)"
echo "OK"
