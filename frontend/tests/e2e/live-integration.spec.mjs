import { test, expect } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000";

test("live frontend critical path uses the running backend", async ({ page, request }) => {
  const suffix = Date.now().toString();
  const email = `frontend-qa-${suffix}@example.com`;
  const password = "FrontendQA123!";
  const jobTitle = `Live QA AI Engineer ${suffix}`;

  const register = await request.post(`${API}/api/v1/auth/register`, {
    data: { email, password, full_name: "Frontend QA" },
  });
  expect(register.ok()).toBeTruthy();

  const login = await request.post(`${API}/api/v1/auth/login`, {
    data: { email, password },
  });
  expect(login.ok()).toBeTruthy();
  const token = (await login.json()).access_token;
  expect(token).toBeTruthy();

  const unauthorized = await request.get(`${API}/api/v1/users/me`);
  expect(unauthorized.status()).toBe(401);

  const me = await request.get(`${API}/api/v1/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(me.ok()).toBeTruthy();

  const jobResponse = await request.post(`${API}/api/v1/jobs`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title: jobTitle,
      company: "Frontend QA",
      location: "Remote",
      job_description: "Build production AI services with Python, PyTorch, Docker and APIs.",
      url: `https://frontend-qa.invalid/jobs/${suffix}`,
      source: "greenhouse",
      application_url: `https://frontend-qa.invalid/apply/${suffix}`,
      work_mode: "remote",
      required_skills: ["Python", "PyTorch"],
      preferred_skills: ["Docker"],
    },
  });
  expect(jobResponse.ok()).toBeTruthy();
  const job = await jobResponse.json();

  const kbGet = await request.get(`${API}/api/v1/profile/kb`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect([200, 404]).toContain(kbGet.status());

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  const meResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/users/me") && response.request().method() === "GET",
  );
  await page.reload();
  expect((await meResponse).status()).toBe(200);

  const jobsPayloadPromise = new Promise((resolve, reject) => {
    const handler = async (response) => {
      if (
        response.url().includes("/api/v1/jobs") &&
        response.request().method() === "GET"
      ) {
        page.off("response", handler);
        try {
          expect(response.status()).toBe(200);
          resolve(await response.json());
        } catch (error) {
          reject(error);
        }
      }
    };
    page.on("response", handler);
  });
  await page.goto("/opportunities");
  const jobsPayload = await jobsPayloadPromise;
  expect(jobsPayload.items.some((item) => item.id === job.id)).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Opportunities" })).toBeVisible();
  await page.getByRole("button", { name: /All/ }).click();
  await expect(page.getByText(jobTitle)).toBeVisible();

  const documentsResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/documents") && response.request().method() === "GET",
  );
  await page.goto("/documents");
  expect((await documentsResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Document Workspace" })).toBeVisible();

  const applicationsResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/applications") && response.request().method() === "GET",
  );
  await page.goto("/applications");
  expect((await applicationsResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Applications" })).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Candidate Profile" })).toBeVisible();

  // Prove the frontend can still reach the API after route transitions.
  const browserJob = await page.evaluate(async ({ api, id }) => {
    const token = localStorage.getItem("aja_token");
    const response = await fetch(`${api}/api/v1/jobs/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return { status: response.status, body: await response.json() };
  }, { api: API, id: job.id });
  expect(browserJob.status).toBe(200);
  expect(browserJob.body.id).toBe(job.id);
});
