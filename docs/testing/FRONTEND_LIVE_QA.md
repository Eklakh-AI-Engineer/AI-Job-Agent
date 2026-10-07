# Frontend live integration QA

Repository tests cover build/type/unit correctness. Live QA must run against a deployed backend and frontend because those environments cannot be represented by static compilation.

## Run

Backend: `LIVE_API_URL=https://api.example.com npm run test:live`
Frontend: `FRONTEND_URL=https://app.example.com npm run test:live:frontend`

## Required browser smoke checklist

- Login succeeds with a disposable test account.
- Invalid credentials show an actionable error.
- Expired/invalid bearer token clears the local session and redirects to login.
- Dashboard loading, empty and error states render correctly.
- Opportunities load from the live jobs API.
- Evaluation displays real ranking components and score.
- Candidate KB save/load round trip succeeds.
- Resume/cover-letter generation reaches the live API.
- Approval gate is visible before application submission.
- Dry-run submission succeeds without external submission.
- Application status and audit events update after the workflow.
