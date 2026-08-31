"""
Cloudera SDX Governance Metadata Tool

Supported operations:
- search_asset
- get_asset_detail
- get_lineage
- get_ranger_context

Purpose:
- Search Apache Atlas metadata
- Retrieve classifications and ownership
- Retrieve lineage
- Correlate Atlas classifications with Apache Ranger resource and tag policies

This tool is read-only.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
import argparse
import json
import requests


# ============================================================
# PARAMETERS
# ============================================================

class UserParameters(BaseModel):
    atlas_url: str
    ranger_url: str
    username: str
    password: str
    verify_ssl: bool = False


class ToolParameters(BaseModel):

    operation: str = Field(
        description=(
            "Operation to execute. Allowed values: "
            "search_asset, get_asset_detail, "
            "get_lineage, get_ranger_context"
        )
    )

    asset_name: Optional[str] = Field(
        default=None,
        description=(
            "Atlas asset name. "
            "Example: candidate_master_sample"
        )
    )

    guid: Optional[str] = Field(
        default=None,
        description=(
            "Atlas GUID for asset detail or lineage lookup"
        )
    )

    database: Optional[str] = Field(
        default=None,
        description=(
            "Database name. Example: danantara"
        )
    )

    table: Optional[str] = Field(
        default=None,
        description=(
            "Table name. Example: candidate_master_sample"
        )
    )

    column: Optional[str] = Field(
        default=None,
        description=(
            "Column name. Example: email"
        )
    )


# ============================================================
# HTTP
# ============================================================

def make_request(
    url: str,
    config: UserParameters,
    params: Optional[dict] = None
) -> dict:

    try:

        response = requests.get(
            url,
            params=params,
            auth=(
                config.username,
                config.password
            ),
            headers={
                "Accept": "application/json"
            },
            verify=config.verify_ssl,
            timeout=30
        )

        result = {
            "request_url": response.url,
            "http_status": response.status_code
        }

        if not response.ok:

            result.update({
                "_error": True,
                "response": response.text[:4000]
            })

            return result

        try:

            result["data"] = response.json()

        except Exception:

            result.update({
                "_error": True,
                "response": response.text[:4000],
                "message": (
                    "Response is not valid JSON"
                )
            })

        return result

    except requests.RequestException as exc:

        return {
            "_error": True,
            "request_url": url,
            "http_status": None,
            "response": None,
            "message": str(exc)
        }


# ============================================================
# ATLAS
# ============================================================

def search_asset(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.asset_name:

        return {
            "status": "error",
            "message": (
                "asset_name is required "
                "for search_asset"
            )
        }

    url = (
        config.atlas_url.rstrip("/")
        + "/v2/search/basic"
    )

    response = make_request(
        url,
        config,
        params={
            "query": args.asset_name,
            "excludeDeletedEntities": "true",
            "limit": 20
        }
    )

    if response.get("_error"):

        return {
            "status": "error",
            "operation": "search_asset",
            **response
        }

    data = response.get("data", {})

    assets = []

    for entity in data.get(
        "entities",
        []
    ):

        attributes = (
            entity.get(
                "attributes",
                {}
            ) or {}
        )

        assets.append({
            "guid": entity.get("guid"),
            "type_name": entity.get(
                "typeName"
            ),
            "name": (
                attributes.get("name")
                or entity.get(
                    "displayText"
                )
            ),
            "qualified_name": (
                attributes.get(
                    "qualifiedName"
                )
            ),
            "owner": attributes.get(
                "owner"
            ),
            "status": entity.get(
                "status"
            ),
            "classifications": (
                entity.get(
                    "classificationNames",
                    []
                )
            )
        })

    return {
        "status": "success",
        "operation": "search_asset",
        "search": args.asset_name,
        "count": len(assets),
        "assets": assets
    }


def get_asset_detail(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.guid:

        return {
            "status": "error",
            "message": (
                "guid is required "
                "for get_asset_detail"
            )
        }

    url = (
        config.atlas_url.rstrip("/")
        + f"/v2/entity/guid/{args.guid}"
    )

    response = make_request(
        url,
        config
    )

    if response.get("_error"):

        return {
            "status": "error",
            "operation": "get_asset_detail",
            **response
        }

    data = response.get("data", {})

    entity = data.get(
        "entity",
        {}
    )

    attributes = (
        entity.get(
            "attributes",
            {}
        ) or {}
    )

    classifications = []

    for item in (
        entity.get(
            "classifications",
            []
        ) or []
    ):

        classifications.append({
            "type_name": item.get(
                "typeName"
            ),
            "attributes": item.get(
                "attributes",
                {}
            ),
            "propagate": item.get(
                "propagate"
            )
        })

    return {
        "status": "success",
        "operation": "get_asset_detail",
        "guid": entity.get(
            "guid"
        ),
        "type_name": entity.get(
            "typeName"
        ),
        "name": attributes.get(
            "name"
        ),
        "qualified_name": (
            attributes.get(
                "qualifiedName"
            )
        ),
        "owner": attributes.get(
            "owner"
        ),
        "description": (
            attributes.get(
                "description"
            )
        ),
        "entity_status": entity.get(
            "status"
        ),
        "created_by": entity.get(
            "createdBy"
        ),
        "updated_by": entity.get(
            "updatedBy"
        ),
        "classifications": (
            classifications
        ),
        "attributes": attributes
    }


def get_lineage(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.guid:

        return {
            "status": "error",
            "message": (
                "guid is required "
                "for get_lineage"
            )
        }

    url = (
        config.atlas_url.rstrip("/")
        + f"/v2/lineage/{args.guid}"
    )

    response = make_request(
        url,
        config,
        params={
            "direction": "BOTH",
            "depth": 3
        }
    )

    if response.get("_error"):

        return {
            "status": "error",
            "operation": "get_lineage",
            **response
        }

    data = response.get("data", {})

    entities = []

    for guid, entity in (
        data.get(
            "guidEntityMap",
            {}
        ) or {}
    ).items():

        attributes = (
            entity.get(
                "attributes",
                {}
            ) or {}
        )

        entities.append({
            "guid": guid,
            "type_name": (
                entity.get(
                    "typeName"
                )
            ),
            "name": (
                attributes.get(
                    "name"
                )
                or entity.get(
                    "displayText"
                )
            ),
            "qualified_name": (
                attributes.get(
                    "qualifiedName"
                )
            ),
            "classifications": (
                entity.get(
                    "classificationNames",
                    []
                )
            )
        })

    return {
        "status": "success",
        "operation": "get_lineage",
        "base_entity_guid": (
            data.get(
                "baseEntityGuid"
            )
        ),
        "entities": entities,
        "relations": data.get(
            "relations",
            []
        )
    }


# ============================================================
# ATLAS COLUMN LOOKUP
# ============================================================

def find_atlas_column(
    config: UserParameters,
    database: str,
    table: str,
    column: str
) -> dict:

    url = (
        config.atlas_url.rstrip("/")
        + "/v2/search/basic"
    )

    response = make_request(
        url,
        config,
        params={
            "query": column,
            "excludeDeletedEntities": "true",
            "limit": 100
        }
    )

    if response.get("_error"):

        return {
            "status": "error",
            **response
        }

    data = response.get(
        "data",
        {}
    )

    matches = []

    db_lower = (
        database.lower()
        if database
        else None
    )

    table_lower = (
        table.lower()
        if table
        else None
    )

    column_lower = column.lower()

    for entity in data.get(
        "entities",
        []
    ):

        attr = (
            entity.get(
                "attributes",
                {}
            ) or {}
        )

        name = str(
            attr.get(
                "name"
            )
            or entity.get(
                "displayText"
            )
            or ""
        )

        qname = str(
            attr.get(
                "qualifiedName"
            )
            or ""
        )

        name_lower = name.lower()
        qname_lower = qname.lower()

        if (
            name_lower != column_lower
            and column_lower not in qname_lower
        ):
            continue

        if (
            db_lower
            and db_lower not in qname_lower
        ):
            continue

        if (
            table_lower
            and table_lower not in qname_lower
        ):
            continue

        matches.append({
            "guid": entity.get(
                "guid"
            ),
            "type_name": entity.get(
                "typeName"
            ),
            "name": name,
            "qualified_name": qname,
            "classifications": (
                entity.get(
                    "classificationNames",
                    []
                )
            )
        })

    return {
        "status": "success",
        "matches": matches
    }


# ============================================================
# RANGER HELPERS
# ============================================================

def resource_values(
    policy: dict,
    possible_names: list
) -> list:

    resources = (
        policy.get(
            "resources",
            {}
        ) or {}
    )

    for name in possible_names:

        if name in resources:

            return (
                resources
                .get(
                    name,
                    {}
                )
                .get(
                    "values",
                    []
                )
            )

    return []


def resource_matches(
    values: list,
    target: Optional[str]
) -> bool:

    if not target:
        return True

    if not values:
        return False

    target = target.lower()

    for value in values:

        value = str(
            value
        ).lower()

        if value == "*":
            return True

        if value == target:
            return True

    return False


def summarize_access_item(
    item: dict
) -> dict:

    return {
        "users": item.get(
            "users",
            []
        ),
        "groups": item.get(
            "groups",
            []
        ),
        "roles": item.get(
            "roles",
            []
        ),
        "accesses": [
            access.get(
                "type"
            )
            for access
            in item.get(
                "accesses",
                []
            )
            if access.get(
                "isAllowed",
                True
            )
        ]
    }


def summarize_policy(
    policy: dict
) -> dict:

    allows = []
    denies = []
    masks = []
    row_filters = []

    for item in (
        policy.get(
            "policyItems",
            []
        ) or []
    ):

        allows.append(
            summarize_access_item(
                item
            )
        )

    for item in (
        policy.get(
            "denyPolicyItems",
            []
        ) or []
    ):

        denies.append(
            summarize_access_item(
                item
            )
        )

    for item in (
        policy.get(
            "dataMaskPolicyItems",
            []
        ) or []
    ):

        mask_info = (
            item.get(
                "dataMaskInfo",
                {}
            ) or {}
        )

        masks.append({
            "users": item.get(
                "users",
                []
            ),
            "groups": item.get(
                "groups",
                []
            ),
            "roles": item.get(
                "roles",
                []
            ),
            "mask_type": (
                mask_info.get(
                    "dataMaskType"
                )
            ),
            "mask_expression": (
                mask_info.get(
                    "valueExpr"
                )
            )
        })

    for item in (
        policy.get(
            "rowFilterPolicyItems",
            []
        ) or []
    ):

        info = (
            item.get(
                "rowFilterInfo",
                {}
            ) or {}
        )

        row_filters.append({
            "users": item.get(
                "users",
                []
            ),
            "groups": item.get(
                "groups",
                []
            ),
            "roles": item.get(
                "roles",
                []
            ),
            "filter_expression": (
                info.get(
                    "filterExpr"
                )
            )
        })

    return {
        "id": policy.get(
            "id"
        ),
        "name": policy.get(
            "name"
        ),
        "service": policy.get(
            "service"
        ),
        "service_type": policy.get(
            "serviceType"
        ),
        "policy_type": policy.get(
            "policyType"
        ),
        "enabled": policy.get(
            "isEnabled"
        ),
        "audit_enabled": (
            policy.get(
                "isAuditEnabled"
            )
        ),
        "description": (
            policy.get(
                "description"
            )
        ),
        "resources": (
            policy.get(
                "resources",
                {}
            )
        ),
        "allow": allows,
        "deny": denies,
        "masking": masks,
        "row_filter": row_filters
    }


def extract_tag_names(
    policy: dict
) -> list:

    resources = (
        policy.get(
            "resources",
            {}
        ) or {}
    )

    possible_keys = [
        "tag",
        "TAG"
    ]

    for key in possible_keys:

        resource = resources.get(
            key
        )

        if resource:

            return resource.get(
                "values",
                []
            ) or []

    return []


# ============================================================
# RANGER CONTEXT
# ============================================================

def get_ranger_context(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.table:

        return {
            "status": "error",
            "message": (
                "table is required "
                "for get_ranger_context"
            )
        }

    # --------------------------------------------------------
    # Step 1 - Atlas column classification
    # --------------------------------------------------------

    atlas_column = None
    classifications = []

    if args.column:

        column_result = find_atlas_column(
            config=config,
            database=args.database,
            table=args.table,
            column=args.column
        )

        if (
            column_result.get(
                "status"
            )
            == "success"
            and column_result.get(
                "matches"
            )
        ):

            atlas_column = (
                column_result[
                    "matches"
                ][0]
            )

            classifications = (
                atlas_column.get(
                    "classifications",
                    []
                )
            )

    # --------------------------------------------------------
    # Step 2 - Retrieve Ranger policies
    # --------------------------------------------------------

    ranger_url = (
        config.ranger_url.rstrip("/")
        + "/service/public/v2/api/policy"
    )

    ranger_response = make_request(
        ranger_url,
        config
    )

    if ranger_response.get(
        "_error"
    ):

        return {
            "status": "error",
            "operation": (
                "get_ranger_context"
            ),
            "request_url": (
                ranger_response.get(
                    "request_url"
                )
            ),
            "http_status": (
                ranger_response.get(
                    "http_status"
                )
            ),
            "response": (
                ranger_response.get(
                    "response"
                )
            ),
            "message": (
                "Failed to retrieve "
                "Ranger policies"
            )
        }

    data = ranger_response.get(
        "data"
    )

    if isinstance(
        data,
        list
    ):

        policies = data

    elif isinstance(
        data,
        dict
    ):

        if "policies" in data:

            policies = data.get(
                "policies",
                []
            )

        else:

            policies = [data]

    else:

        policies = []

    resource_policies = []
    tag_policies = []

    # --------------------------------------------------------
    # Step 3 - Resource policies
    # --------------------------------------------------------

    for policy in policies:

        db_values = resource_values(
            policy,
            [
                "database",
                "hive_database"
            ]
        )

        table_values = resource_values(
            policy,
            [
                "table",
                "hive_table"
            ]
        )

        column_values = resource_values(
            policy,
            [
                "column",
                "hive_column"
            ]
        )

        # Ignore non-resource policies
        if (
            not db_values
            and not table_values
            and not column_values
        ):
            continue

        if not resource_matches(
            db_values,
            args.database
        ):
            continue

        if not resource_matches(
            table_values,
            args.table
        ):
            continue

        if (
            args.column
            and not resource_matches(
                column_values,
                args.column
            )
        ):
            continue

        resource_policies.append(
            summarize_policy(
                policy
            )
        )

    # --------------------------------------------------------
    # Step 4 - Tag policies
    # --------------------------------------------------------

    class_lower = [
        str(x).lower()
        for x in classifications
    ]

    for policy in policies:

        tags = extract_tag_names(
            policy
        )

        if not tags:
            continue

        matched_tags = []

        for tag in tags:

            if (
                str(tag).lower()
                in class_lower
            ):

                matched_tags.append(
                    tag
                )

        if not matched_tags:
            continue

        summary = summarize_policy(
            policy
        )

        summary[
            "matched_atlas_tags"
        ] = matched_tags

        tag_policies.append(
            summary
        )

    # --------------------------------------------------------
    # Step 5 - Effective masking context
    # --------------------------------------------------------

    masking_context = []

    for policy in tag_policies:

        for mask in policy.get(
            "masking",
            []
        ):

            masking_context.append({
                "policy_name": (
                    policy.get(
                        "name"
                    )
                ),
                "tags": policy.get(
                    "matched_atlas_tags",
                    []
                ),
                "users": mask.get(
                    "users",
                    []
                ),
                "groups": mask.get(
                    "groups",
                    []
                ),
                "roles": mask.get(
                    "roles",
                    []
                ),
                "mask_type": (
                    mask.get(
                        "mask_type"
                    )
                ),
                "mask_expression": (
                    mask.get(
                        "mask_expression"
                    )
                ),
                "audit_enabled": (
                    policy.get(
                        "audit_enabled"
                    )
                )
            })

    return {
        "status": "success",
        "operation": (
            "get_ranger_context"
        ),

        "database": args.database,
        "table": args.table,
        "column": args.column,

        "atlas_column": atlas_column,

        "atlas_classifications": (
            classifications
        ),

        "ranger_request_url": (
            ranger_response.get(
                "request_url"
            )
        ),

        "ranger_http_status": (
            ranger_response.get(
                "http_status"
            )
        ),

        "total_ranger_policies": len(
            policies
        ),

        "matched_resource_policy_count": (
            len(
                resource_policies
            )
        ),

        "matched_tag_policy_count": (
            len(
                tag_policies
            )
        ),

        "resource_policies": (
            resource_policies
        ),

        "tag_policies": (
            tag_policies
        ),

        "effective_masking_context": (
            masking_context
        ),

        "governance_correlation": {
            "atlas_tag_found": (
                len(
                    classifications
                ) > 0
            ),
            "matching_ranger_tag_policy_found": (
                len(
                    tag_policies
                ) > 0
            ),
            "masking_policy_found": (
                len(
                    masking_context
                ) > 0
            )
        }
    }


# ============================================================
# MAIN DISPATCH
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

    if operation == "search_asset":

        return search_asset(
            config,
            args
        )

    if operation == "get_asset_detail":

        return get_asset_detail(
            config,
            args
        )

    if operation == "get_lineage":

        return get_lineage(
            config,
            args
        )

    if operation == "get_ranger_context":

        return get_ranger_context(
            config,
            args
        )

    return {
        "status": "error",
        "message": (
            "Unsupported operation. "
            "Allowed operations: "
            "search_asset, "
            "get_asset_detail, "
            "get_lineage, "
            "get_ranger_context"
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
        required=True,
        help="Tool configuration"
    )

    parser.add_argument(
        "--tool-params",
        required=True,
        help="Tool arguments"
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