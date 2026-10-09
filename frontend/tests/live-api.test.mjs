import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

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


const qaEmail = process.env.LIVE_QA_EMAIL;
const qaPassword = process.env.LIVE_QA_PASSWORD;
const authenticatedQaEnabled = Boolean(apiUrl && qaEmail && qaPassword);

test("authenticated production smoke and sanitized persisted-job export", {
  skip: !authenticatedQaEnabled,
}, async () => {
  const loginResponse = await fetch(`${apiUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: qaEmail, password: qaPassword }),
  });
  assert.equal(loginResponse.status, 200, "test account login must succeed");
  const loginBody = await loginResponse.json();
  assert.ok(loginBody.access_token, "login response must contain an access token");

  const headers = { authorization: `Bearer ${loginBody.access_token}` };
  const profileResponse = await fetch(`${apiUrl}/api/v1/users/me`, { headers });
  assert.equal(profileResponse.status, 200, "authenticated profile read must succeed");
  const profile = await profileResponse.json();
  assert.ok(profile.id, "profile response must contain a user ID");

  const jobsResponse = await fetch(`${apiUrl}/api/v1/jobs?limit=500&offset=0`, { headers });
  assert.equal(jobsResponse.status, 200, "authenticated job listing must succeed");
  const jobsBody = await jobsResponse.json();
  assert.ok(Array.isArray(jobsBody.items), "job listing must contain an items array");
  assert.ok(jobsBody.total > 0, "production must contain persisted job postings");
  assert.ok(jobsBody.items.length > 0, "job export must contain at least one record");

  const sanitizedJobs = jobsBody.items.map((job) => ({
    id: job.id,
    source_job_id: job.source_job_id ?? null,
    title: job.title,
    company: job.company,
    url: job.url,
    source: job.source,
    location: job.location ?? null,
    work_mode: job.work_mode ?? null,
    job_description_sha256: createHash("sha256")
      .update(job.job_description ?? "")
      .digest("hex"),
  }));
  const exportPath = process.env.JOB_EXPORT_PATH;
  if (exportPath) {
    const target = resolve(process.cwd(), exportPath);
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, JSON.stringify({
      captured_at_utc: new Date().toISOString(),
      source: "authenticated_production_api",
      total_available: jobsBody.total,
      items_exported: sanitizedJobs.length,
      production_authoritative: false,
      note: "Sanitized metadata export; review and map IDs before benchmark promotion.",
      jobs: sanitizedJobs,
    }, null, 2) + "\n", { encoding: "utf-8", mode: 0o600 });
  }
  console.log(`authenticated production smoke passed; persisted jobs exported: ${sanitizedJobs.length}`);
});
