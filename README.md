# FiDa

**FiDa** (pronounced *Fai-da*) is a smart personal finance dashboard
that helps you understand, track, and improve your financial life.

> A smarter way to see your money.

## Encryption rollout

- Set `ENFORCE_ENCRYPTED_WRITES=false` during migration/backfill windows.
- Set `ENFORCE_ENCRYPTED_WRITES=true` to require encrypted payload writes for sensitive account/category/transaction fields.
- Apply latest migrations before enabling strict mode:
	- `20260321_0002_profile_encryption_key_material`
	- `20260321_0003_encrypted_payload_columns`