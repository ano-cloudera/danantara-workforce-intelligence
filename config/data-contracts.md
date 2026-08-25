# PoC Data Contracts

## Candidate view
Expected fields: `candidate_id`, `name`, `company`, `years_experience`, `skills`, `summary`.

## Position view
Expected fields: `position_id`, `title`, `required_skills`, `preferred_skills`, `min_years_experience`.

## Policy vector payload
Expected metadata: `entity`, `title`, `page`, `text`, `source_path`.

These contracts are deliberately small so the PoC can map existing curated customer tables/views without forcing a new enterprise canonical model.
