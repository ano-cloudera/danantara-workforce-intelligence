"""
Talent Intelligence Tool for Danantara Workforce Intelligence.

Supported operations:
- list_candidates
- get_candidate_profile
- get_candidate_skills
- list_job_positions
- get_job_position
- match_candidates

Data source:
Cloudera Impala / CDW

This tool is read-only.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from impala.dbapi import connect
import argparse
import json
import re


# ============================================================
# PARAMETERS
# ============================================================

class UserParameters(BaseModel):
    """
    Connection configuration.

    Example:
    impala_host = <CDW / Impala endpoint>
    impala_port = 443
    database = danantara
    username = workload username
    password = workload password
    use_ssl = true
    http_path = cliservice
    """

    impala_host: str
    impala_port: int = 443
    database: str = "danantara"

    username: str
    password: str

    use_ssl: bool = True
    http_path: str = "cliservice"


class ToolParameters(BaseModel):

    operation: str = Field(
        description=(
            "Operation to execute. Allowed values: "
            "list_candidates, get_candidate_profile, "
            "get_candidate_skills, list_job_positions, "
            "get_job_position, match_candidates"
        )
    )

    candidate_id: Optional[str] = Field(
        default=None,
        description="Candidate ID such as CAND-BNS-0003"
    )

    position_id: Optional[str] = Field(
        default=None,
        description="Job position ID such as REQ-ENP-002"
    )

    entity: Optional[str] = Field(
        default=None,
        description="Optional company/entity filter such as BNS or ENP"
    )

    title: Optional[str] = Field(
        default=None,
        description="Optional candidate or job title filter"
    )

    skill: Optional[str] = Field(
        default=None,
        description="Optional skill filter"
    )

    min_years_experience: Optional[float] = Field(
        default=None,
        description="Optional minimum years of candidate experience"
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results"
    )


# ============================================================
# IMPALA
# ============================================================

def get_connection(config: UserParameters):

    return connect(
        host=config.impala_host,
        port=config.impala_port,
        user=config.username,
        password=config.password,
        database=config.database,
        auth_mechanism="PLAIN",
        use_ssl=config.use_ssl,
        use_http_transport=True,
        http_path=config.http_path
    )


def run_query(
    config: UserParameters,
    sql: str,
    params: Optional[list] = None
) -> list:

    conn = get_connection(config)

    try:

        cursor = conn.cursor()

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        columns = [
            desc[0]
            for desc in cursor.description
        ]

        rows = cursor.fetchall()

        result = []

        for row in rows:

            result.append(
                dict(
                    zip(
                        columns,
                        row
                    )
                )
            )

        return result

    finally:

        try:
            cursor.close()
        except Exception:
            pass

        conn.close()


# ============================================================
# HELPERS
# ============================================================

def normalize_skill(skill: str) -> str:

    if not skill:
        return ""

    skill = skill.lower().strip()

    skill = re.sub(
        r"\s+",
        " ",
        skill
    )

    return skill


def parse_skills(value: Any) -> list:

    if value is None:
        return []

    if isinstance(value, list):
        raw = value

    else:
        text = str(value)

        raw = re.split(
            r"[,;|]",
            text
        )

    cleaned = []

    for skill in raw:

        normalized = normalize_skill(
            str(skill)
        )

        if normalized:
            cleaned.append(
                normalized
            )

    return list(
        dict.fromkeys(
            cleaned
        )
    )


def skill_display_map(skills: list) -> dict:

    return {
        normalize_skill(x): x
        for x in skills
        if x
    }


# ============================================================
# CANDIDATES
# ============================================================

def list_candidates(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    sql = f"""
    SELECT
        candidate_id,
        name,
        company,
        current_title,
        years_experience,
        city,
        education_level,
        education_institution,
        skills,
        summary
    FROM {config.database}.v_candidates_api
    WHERE 1 = 1
    """

    conditions = []

    if args.entity:

        safe_entity = (
            args.entity
            .replace("'", "''")
        )

        conditions.append(
            f"UPPER(company) = UPPER('{safe_entity}')"
        )

    if args.title:

        safe_title = (
            args.title
            .replace("'", "''")
        )

        conditions.append(
            f"LOWER(current_title) LIKE LOWER('%{safe_title}%')"
        )

    if args.skill:

        safe_skill = (
            args.skill
            .replace("'", "''")
        )

        conditions.append(
            f"LOWER(skills) LIKE LOWER('%{safe_skill}%')"
        )

    if args.min_years_experience is not None:

        conditions.append(
            f"years_experience >= {float(args.min_years_experience)}"
        )

    if conditions:

        sql += (
            " AND "
            + " AND ".join(
                conditions
            )
        )

    sql += (
        f" ORDER BY years_experience DESC "
        f"LIMIT {args.limit}"
    )

    rows = run_query(
        config,
        sql
    )

    return {
        "status": "success",
        "operation": "list_candidates",
        "count": len(rows),
        "candidates": rows
    }


def get_candidate_profile(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.candidate_id:

        return {
            "status": "error",
            "message": (
                "candidate_id is required "
                "for get_candidate_profile"
            )
        }

    candidate_id = (
        args.candidate_id
        .replace("'", "''")
    )

    profile_sql = f"""
    SELECT
        candidate_id,
        name,
        company,
        current_title,
        years_experience,
        city,
        education_level,
        education_institution,
        skills,
        summary
    FROM {config.database}.v_candidates_api
    WHERE candidate_id = '{candidate_id}'
    LIMIT 1
    """

    skills_sql = f"""
    SELECT
        candidate_id,
        skill_name,
        proficiency_score
    FROM {config.database}.candidate_skills
    WHERE candidate_id = '{candidate_id}'
    ORDER BY proficiency_score DESC
    """

    experience_sql = f"""
    SELECT *
    FROM {config.database}.candidate_experience
    WHERE candidate_id = '{candidate_id}'
    """

    profile = run_query(
        config,
        profile_sql
    )

    if not profile:

        return {
            "status": "not_found",
            "operation": "get_candidate_profile",
            "candidate_id": args.candidate_id
        }

    skills = run_query(
        config,
        skills_sql
    )

    experience = run_query(
        config,
        experience_sql
    )

    return {
        "status": "success",
        "operation": "get_candidate_profile",
        "candidate": profile[0],
        "skills": skills,
        "experience": experience
    }


def get_candidate_skills(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.candidate_id:

        return {
            "status": "error",
            "message": (
                "candidate_id is required "
                "for get_candidate_skills"
            )
        }

    candidate_id = (
        args.candidate_id
        .replace("'", "''")
    )

    sql = f"""
    SELECT
        candidate_id,
        skill_name,
        proficiency_score
    FROM {config.database}.candidate_skills
    WHERE candidate_id = '{candidate_id}'
    ORDER BY proficiency_score DESC
    """

    rows = run_query(
        config,
        sql
    )

    return {
        "status": "success",
        "operation": "get_candidate_skills",
        "candidate_id": args.candidate_id,
        "count": len(rows),
        "skills": rows
    }


# ============================================================
# JOB POSITIONS
# ============================================================

def list_job_positions(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    sql = f"""
    SELECT *
    FROM {config.database}.curated_job_positions
    WHERE 1 = 1
    """

    conditions = []

    if args.entity:

        safe_entity = (
            args.entity
            .replace("'", "''")
        )

        conditions.append(
            f"UPPER(entity) = UPPER('{safe_entity}')"
        )

    if args.title:

        safe_title = (
            args.title
            .replace("'", "''")
        )

        conditions.append(
            f"LOWER(title) LIKE LOWER('%{safe_title}%')"
        )

    if conditions:

        sql += (
            " AND "
            + " AND ".join(
                conditions
            )
        )

    sql += (
        f" ORDER BY position_id "
        f"LIMIT {args.limit}"
    )

    rows = run_query(
        config,
        sql
    )

    return {
        "status": "success",
        "operation": "list_job_positions",
        "count": len(rows),
        "positions": rows
    }


def get_job_position(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.position_id:

        return {
            "status": "error",
            "message": (
                "position_id is required "
                "for get_job_position"
            )
        }

    position_id = (
        args.position_id
        .replace("'", "''")
    )

    sql = f"""
    SELECT *
    FROM {config.database}.curated_job_positions
    WHERE position_id = '{position_id}'
    LIMIT 1
    """

    rows = run_query(
        config,
        sql
    )

    if not rows:

        return {
            "status": "not_found",
            "operation": "get_job_position",
            "position_id": args.position_id
        }

    return {
        "status": "success",
        "operation": "get_job_position",
        "position": rows[0]
    }


# ============================================================
# MATCHING
# ============================================================

def match_candidates(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.position_id:

        return {
            "status": "error",
            "message": (
                "position_id is required "
                "for match_candidates"
            )
        }

    position_id = (
        args.position_id
        .replace("'", "''")
    )

    job_sql = f"""
    SELECT *
    FROM {config.database}.curated_job_positions
    WHERE position_id = '{position_id}'
    LIMIT 1
    """

    jobs = run_query(
        config,
        job_sql
    )

    if not jobs:

        return {
            "status": "not_found",
            "operation": "match_candidates",
            "position_id": args.position_id,
            "message": "Job position not found"
        }

    job = jobs[0]

    required_skills_original = parse_skills(
        job.get(
            "required_skills"
        )
    )

    preferred_skills_original = parse_skills(
        job.get(
            "preferred_skills"
        )
    )

    required_skills = {
        normalize_skill(x)
        for x in required_skills_original
    }

    preferred_skills = {
        normalize_skill(x)
        for x in preferred_skills_original
    }

    min_years = (
        float(
            job.get(
                "min_years_experience"
            )
            or 0
        )
    )

    candidate_sql = f"""
    SELECT
        candidate_id,
        name,
        company,
        current_title,
        years_experience,
        city,
        education_level,
        education_institution,
        skills,
        summary
    FROM {config.database}.v_candidates_api
    """

    candidate_rows = run_query(
        config,
        candidate_sql
    )

    skills_sql = f"""
    SELECT
        candidate_id,
        skill_name,
        proficiency_score
    FROM {config.database}.candidate_skills
    """

    skills_rows = run_query(
        config,
        skills_sql
    )

    candidate_skill_map = {}

    for row in skills_rows:

        candidate_id = row.get(
            "candidate_id"
        )

        if candidate_id not in candidate_skill_map:
            candidate_skill_map[
                candidate_id
            ] = []

        candidate_skill_map[
            candidate_id
        ].append({
            "skill_name": row.get(
                "skill_name"
            ),
            "proficiency_score": row.get(
                "proficiency_score"
            )
        })

    rankings = []

    for candidate in candidate_rows:

        candidate_id = candidate.get(
            "candidate_id"
        )

        structured_skills = (
            candidate_skill_map.get(
                candidate_id,
                []
            )
        )

        candidate_skills = set()

        skill_display = {}

        for item in structured_skills:

            skill_name = item.get(
                "skill_name"
            )

            if skill_name:

                normalized = normalize_skill(
                    skill_name
                )

                candidate_skills.add(
                    normalized
                )

                skill_display[
                    normalized
                ] = skill_name

        for skill_name in parse_skills(
            candidate.get(
                "skills"
            )
        ):

            normalized = normalize_skill(
                skill_name
            )

            candidate_skills.add(
                normalized
            )

            if normalized not in skill_display:

                skill_display[
                    normalized
                ] = skill_name

        matched_required = (
            required_skills
            .intersection(
                candidate_skills
            )
        )

        missing_required = (
            required_skills
            .difference(
                candidate_skills
            )
        )

        matched_preferred = (
            preferred_skills
            .intersection(
                candidate_skills
            )
        )

        if required_skills:

            required_score = (
                len(
                    matched_required
                )
                / len(
                    required_skills
                )
            ) * 70

        else:

            required_score = 70

        if preferred_skills:

            preferred_score = (
                len(
                    matched_preferred
                )
                / len(
                    preferred_skills
                )
            ) * 10

        else:

            preferred_score = 10

        years = float(
            candidate.get(
                "years_experience"
            )
            or 0
        )

        if min_years <= 0:

            experience_score = 20

        elif years >= min_years:

            experience_score = 20

        else:

            experience_score = max(
                0,
                (
                    years
                    / min_years
                ) * 20
            )

        total_score = (
            required_score
            + preferred_score
            + experience_score
        )

        rankings.append({
            "candidate_id": candidate_id,
            "name": candidate.get(
                "name"
            ),
            "company": candidate.get(
                "company"
            ),
            "current_title": (
                candidate.get(
                    "current_title"
                )
            ),
            "years_experience": years,

            "match_score": round(
                total_score,
                1
            ),

            "matched_required_skills": [
                skill_display.get(
                    skill,
                    skill
                )
                for skill in sorted(
                    matched_required
                )
            ],

            "missing_required_skills": [
                skill
                for skill in sorted(
                    missing_required
                )
            ],

            "matched_preferred_skills": [
                skill_display.get(
                    skill,
                    skill
                )
                for skill in sorted(
                    matched_preferred
                )
            ],

            "experience_requirement": (
                min_years
            ),

            "experience_requirement_met": (
                years >= min_years
            ),

            "score_breakdown": {
                "required_skills": round(
                    required_score,
                    1
                ),
                "preferred_skills": round(
                    preferred_score,
                    1
                ),
                "experience": round(
                    experience_score,
                    1
                )
            }
        })

    rankings.sort(
        key=lambda x: x[
            "match_score"
        ],
        reverse=True
    )

    rankings = rankings[
        :args.limit
    ]

    return {
        "status": "success",
        "operation": "match_candidates",

        "position": {
            "position_id": job.get(
                "position_id"
            ),
            "title": job.get(
                "title"
            ),
            "entity": job.get(
                "entity"
            ),
            "grade": job.get(
                "grade"
            ),
            "level": job.get(
                "level"
            ),
            "department": job.get(
                "department"
            ),
            "required_skills": (
                required_skills_original
            ),
            "preferred_skills": (
                preferred_skills_original
            ),
            "min_years_experience": (
                min_years
            )
        },

        "scoring_method": {
            "required_skills_weight": 70,
            "preferred_skills_weight": 10,
            "experience_weight": 20,
            "maximum_score": 100
        },

        "candidate_count": len(
            rankings
        ),

        "rankings": rankings,

        "advisory": (
            "Candidate ranking is decision support only. "
            "Final hiring decisions require human review."
        )
    }


# ============================================================
# DISPATCH
# ============================================================

def run_tool(
    config: UserParameters,
    args: ToolParameters
) -> Any:

    operation = (
        args.operation
        .strip()
        .lower()
    )

    if operation == "list_candidates":

        return list_candidates(
            config,
            args
        )

    if operation == "get_candidate_profile":

        return get_candidate_profile(
            config,
            args
        )

    if operation == "get_candidate_skills":

        return get_candidate_skills(
            config,
            args
        )

    if operation == "list_job_positions":

        return list_job_positions(
            config,
            args
        )

    if operation == "get_job_position":

        return get_job_position(
            config,
            args
        )

    if operation == "match_candidates":

        return match_candidates(
            config,
            args
        )

    return {
        "status": "error",
        "message": (
            "Unsupported operation. "
            "Allowed operations: "
            "list_candidates, "
            "get_candidate_profile, "
            "get_candidate_skills, "
            "list_job_positions, "
            "get_job_position, "
            "match_candidates"
        )
    }


# ============================================================
# CLI
# ============================================================

OUTPUT_KEY = "tool_output"


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--user-params",
        required=True
    )

    parser.add_argument(
        "--tool-params",
        required=True
    )

    cli = parser.parse_args()

    try:

        config = UserParameters(
            **json.loads(
                cli.user_params
            )
        )

        params = ToolParameters(
            **json.loads(
                cli.tool_params
            )
        )

        output = run_tool(
            config,
            params
        )

        print(
            OUTPUT_KEY,
            json.dumps(
                output,
                default=str
            )
        )

    except Exception as exc:

        print(
            OUTPUT_KEY,
            json.dumps({
                "status": "error",
                "error_type": (
                    type(exc).__name__
                ),
                "message": str(exc)
            })
        )