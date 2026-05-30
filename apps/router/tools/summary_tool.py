from typing import Any

from apps.router.llm import get_llm_provider
from apps.router.llm.exceptions import LLMProviderError
from apps.router.tools.base import BaseTool
from apps.router.tools.exceptions import ToolExecutionError
from apps.router.tools.responses import tool_response

SUMMARY_PROMPT_TEMPLATE = (
    "Summarize the following text in 2-4 concise sentences. "
    "Return only the summary with no preamble.\n\n{text}"
)


class SummaryTool(BaseTool):
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        text = parameters["text"]

        try:
            summary = get_llm_provider().complete(
                SUMMARY_PROMPT_TEMPLATE.format(text=text)
            )
        except LLMProviderError as exc:
            raise ToolExecutionError(f"Summary generation failed: {exc}") from exc

        return tool_response(
            success=True,
            data={
                "summary": summary.strip(),
                "source_length": len(text),
            },
        )
