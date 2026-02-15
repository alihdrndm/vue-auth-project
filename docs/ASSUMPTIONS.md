# Verified vs assumed

Statements in the specification that were **not** verified against a real system. Each keeps its ID so it can be traced back. When one is verified (or proved wrong), its entry says so, with the date.

| ID | Assumption | Why it matters | Status |
|----|------------|----------------|--------|
| E1 | Hybrid PDFs are not checked for PDF/A-3 conformance. That check needs veraPDF, a Java tool, and is out of scope. A ZUGFeRD/Factur-X file whose embedded XML is valid is treated as valid, even if its PDF part would fail PDF/A-3. | A real recipient may reject a non-conformant PDF/A-3 file, which Eingang would accept. | Assumed |
| E2 | Vercel limits a proxied request body to about 4.5 MB. So uploads are capped at 4 MB per file, and the frontend sends one file per request. | If the real limit is lower, uploads near 4 MB would fail at the proxy before reaching the API. | Assumed |
| E3 | BASIC and EXTENDED profiles are validated against XSD and the EN 16931 rules only. The profile-specific Factur-X Schematron is not applied. EXTENDED invoices may therefore produce EN 16931 findings that the Factur-X EXTENDED profile allows. | The UI says "Checked against EN 16931 rules only" for these profiles. | Assumed |
| E5 | XRechnung 1.x and 2.x files are validated against XSD and the EN 16931 rules only, because the vendored rules are for XRechnung 3.0. | The UI says "XRechnung 2.x: checked against EN 16931 rules only". | Assumed |
| H1 | The daily maintenance schedule touches the database, and that keeps the free Supabase project from pausing after a week of inactivity. If it pauses anyway, it can be restored from the Supabase dashboard at no cost (see `docs/DEPLOY.md`). | The public demo would be offline until restored. | Assumed |
| H2 | Railway's lowest usage hard limit is USD 10 per month. | `docs/DEPLOY.md` step 0 tells the owner to set it, so the bill is capped. | Assumed; check on Railway's usage settings page before deploying |
