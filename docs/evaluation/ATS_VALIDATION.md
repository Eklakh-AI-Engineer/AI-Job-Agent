# ATS Validation

## Safety boundary

Real-ATS validation is **dry-run only**. The validator may navigate to a public
application form and fill disposable values in the browser, but it never clicks
the submit button and never sends an application.

## Controlled mock ATS

tests/e2e/test_mock_ats_application.py exercises the real Playwright form filler
against a local ATS-like form.

The test verifies:

- form fields resolve through the configured selectors;
- resume and cover-letter upload inputs are populated;
- dry-run mode never submits;
- real-submit mode reaches the controlled local submit endpoint;
- no external service or applicant data is involved.

Run:

    pytest tests/e2e/test_mock_ats_application.py -m e2e

The test requires the Playwright Chromium browser.

## Real ATS validation

Use the validator with a current public application URL:

    python scripts/validate_real_ats.py --url "https://boards.greenhouse.io/..."

The validator records the ATS resolved, fields filled, dry-run state and errors.
It uses disposable example.invalid identity values and never submits.

Recommended provider coverage:

| ATS | Evidence |
|---|---|
| Greenhouse | public form loads, selector map resolves, resume upload resolves, dry-run completes |
| Lever | public form loads, selector map resolves, resume upload resolves, dry-run completes |
| Workday | public application flow loads, selector map resolves, resume upload resolves, dry-run completes |

Real ATS pages change frequently. Record the exact URL and UTC timestamp with
each validation result. A live page inspection is not itself proof that our
automation succeeded; the executable validator is the source of truth.


## CI evidence

The repository includes `.github/workflows/real-ats-validation.yml`, which runs the validator against current public Lever application pages with disposable data and `dry_run=True`. The workflow is non-submitting by construction.
