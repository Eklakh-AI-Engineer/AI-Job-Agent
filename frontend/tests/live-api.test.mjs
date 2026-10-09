import test from "node:test";
import assert from "node:assert/strict";

const apiUrl = process.env.LIVE_API_URL?.replace(/\/$/, "");

test("live backend health remains stable across repeated database probes", { skip: !apiUrl }, async () => {
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    const response = await fetch(`${apiUrl}/health?release_audit_probe=${attempt}`);
    assert.equal(response.status, 200, `health probe ${attempt} returned HTTP ${response.status}`);
    const body = await response.json();
    assert.equal(body.status, "ok", `health probe ${attempt} was not ok`);
    assert.equal(body.database, "healthy", `health probe ${attempt} reported database=${body.database}`);
  }
});

test("live backend rejects unauthenticated protected access", { skip: !apiUrl }, async () => {
  const response = await fetch(`${apiUrl}/api/v1/users/me`);
  assert.ok([401, 403].includes(response.status));
});


test("live job listing rejects unauthenticated access", { skip: !apiUrl }, async () => {
  const response = await fetch(`${apiUrl}/api/v1/jobs?limit=1`);
  assert.ok([401, 403].includes(response.status));
});
