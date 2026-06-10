---
name: Telemetry V2 credential durability false-confidence
description: Why telemetry V2 can report "durable (GCP)" yet fail every Secret Manager call, and how in-memory creds vanish on restart.
---

- Telemetry V2 picks its credential backend once at import. The durability check is **type-based**: it returns "durable" if the store is the GCP class, decided only from `gcp_project_id` + `GOOGLE_APPLICATION_CREDENTIALS_JSON` being present and the client initializing. It NEVER makes a live Secret Manager API call.
- Consequence: a wrong-project or unauthorized service account passes the production boot guard (logs "durable (GCP)") and the in-production write/test guard, but every real store/retrieve/create then fails `403` (e.g. `CONSUMER_INVALID` on the target project). The fingerprint/retrieve path swallows the error and returns `{}` → sync/test surface "No credentials are stored" / "Provider call failed".
- Tell-tale: the `GOOGLE_APPLICATION_CREDENTIALS_JSON` service-account `project_id` must match `gcp_project_id` (or the SA must be IAM-granted on that project AND Secret Manager API enabled + billing active there). A mismatch is the signature of this failure.
- Related: the secret reference name (`ilios-telemetry-v2-c{company}-{hex}`) is identical between the in-memory and GCP stores. Credentials saved while on the in-memory backend (before GCP was configured, or when GCP init silently fell back) are LOST on process restart; the DB row keeps `secret_token_name` + `credential_status` but the secret never existed in GCP.

**Why:** Real incident — after creds were entered and a 71-site AlsoEnergy sync succeeded within one dev process lifetime (in-memory), a restart wiped them; the now-selected GCP store 403'd (CONSUMER_INVALID, SA belonged to a different project), so creds "appeared missing" and could not be re-entered durably. The prior `telemetry_sites_mapping` column addition (company_id/created_by_user_id) was NOT the cause — only the coincidental restart timing was.

**How to apply:** When telemetry creds "disappear" or sync fails with no-credentials / ConnectionError, run a LIVE Secret Manager healthcheck (create→add→access→delete a throwaway secret under the `ilios-telemetry-v2-` prefix) before trusting the "durable" status or asking the user to re-enter creds. A failed sync never wipes cached `telemetry_external_sites` or `telemetry_sites_mapping` rows (verified: 71 cached sites survived a failed sync), so mappings are safe to leave in place.
