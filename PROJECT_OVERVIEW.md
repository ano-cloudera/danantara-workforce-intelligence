# Project Overview

## Name
Danantara Workforce Intelligence PoC

## Goal
Demonstrate how a governed Cloudera on Cloud data foundation can support both management analytics and AI-driven workforce intelligence for candidate screening and policy understanding.

## Personas

### HR / Talent Analyst
Needs multi-step candidate matching, ranking, skill-gap reasoning, and evidence-backed recommendations.

### HR Business User / Policy User
Needs conversational policy search, comparison, summarization, and citations without learning SQL or navigating raw documents.

### HR Management
Needs monitoring of total candidates, recruitment activity, skills, companies and candidate pipeline through Cloudera Data Visualization.

## Primary business scenarios

1. Rank the best candidates for a selected role and explain the gaps.
2. Compare a policy topic across BNS, ENP and NHS with source citations.
3. Monitor candidate and recruitment KPIs on a governed management dashboard.

## Technical position

- Agent Studio remains available as a Cloudera-native workflow showcase.
- The PoC runtime uses a custom backend so Gemini can be used consistently for both LLM generation and embeddings.
- The custom backend uses CrewAI Flows to orchestrate business steps while calling Gemini directly through the Google Gen AI SDK.
