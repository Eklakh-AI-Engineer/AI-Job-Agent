import test from "node:test";
import assert from "node:assert/strict";

const apiUrl = process.env.LIVE_API_URL?.replace(/\/$/, "");

test("live backend health endpoint", { skip: !apiUrl }, async () => {
  const response = await fetch(`${apiUrl}/health`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, "ok");
});

test("live backend rejects unauthenticated protected access", { skip: !apiUrl }, async () => {
  const response = await fetch(`${apiUrl}/api/v1/users/me`);
  assert.ok([401, 403].includes(response.status));
});
