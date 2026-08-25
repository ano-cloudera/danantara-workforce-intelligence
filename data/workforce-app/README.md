# Workforce application data

This directory contains local-only data owned by Danantara Workforce Intelligence:

- `demo/`: committed, non-sensitive fallback fixtures.
- `uploads/`: runtime uploads handled by the backend fallback.
- `app_state.db`: runtime application state only; never candidate system-of-record data.

Workforce candidate and policy vectors use the collections configured by
`QDRANT_CANDIDATE_COLLECTION` and `QDRANT_POLICY_COLLECTION`.
