from __future__ import annotations

import json
from typing import Any

from app.db import models
from app.services.workflow_definition_service import get_workflow, latest_published


class PeeweeDefinitionPort:
    def load_published_runtime(self, workflow_id: str, version: int | None = None) -> dict[str, Any]:
        if version is None:
            ver = latest_published(workflow_id)
        else:
            wf = get_workflow(workflow_id)
            ver = models.WorkflowVersion.get_or_none(
                (models.WorkflowVersion.workflow == wf)
                & (models.WorkflowVersion.version == int(version))
                & (models.WorkflowVersion.state == "published")
            )
        if not ver:
            raise RuntimeError(f"subflow not published: {workflow_id}")
        return json.loads(ver.dsl_json)
