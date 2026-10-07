import test from "node:test";
import assert from "node:assert/strict";

const frontendUrl = process.env.FRONTEND_URL?.replace(/\/$/, "");

test("live frontend serves the application shell", { skip: !frontendUrl }, async () => {
  const response = await fetch(frontendUrl);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<html/i);
});
