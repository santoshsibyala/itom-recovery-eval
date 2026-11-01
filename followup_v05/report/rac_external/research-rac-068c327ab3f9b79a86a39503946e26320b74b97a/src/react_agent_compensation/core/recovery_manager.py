"""Recovery Manager - the brain of the compensation system.

Orchestrates retry, alternatives, and rollback logic for compensatable
tool executions.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from react_agent_compensation.core.config import AlternativeMap, CompensationPairs, RetryPolicy
from react_agent_compensation.core.exceptions import CriticalFailure, ExtractionError, RollbackFailure
from react_agent_compensation.core.extraction import create_extraction_strategy
from react_agent_compensation.core.extraction.base import ExtractionStrategy
from react_agent_compensation.core.extraction.path_resolver import extract_all_values
from react_agent_compensation.core.errors.permanent import is_likely_permanent
from react_agent_compensation.core.models import ActionRecord, ActionStatus, FailureContext
from react_agent_compensation.core.protocols import ActionExecutor
from react_agent_compensation.core.retry import ExponentialBackoffStrategy, RetryContext, RetryStrategy
from react_agent_compensation.core.transaction_log import TransactionLog

if TYPE_CHECKING:
    from react_agent_compensation.core.errors.base import ErrorStrategy


logger = logging.getLogger(__name__)


# Prompt template for LLM-based tool alternative discovery.
# Only used when enable_tool_alternatives is True.
TOOL_ALTERNATIVE_PROMPT = """CONTEXT: enable_tool_alternatives : enabled
You are a resilience coordination system for an AI agent.
An action has failed, and we need to find an alternative tool that can achieve the same goal.

Failed Action: {action}
Parameters: {params}
Error: {error}

Available Tools:
{tools_list}

IMPORTANT: Identify an alternative tool that could achieve the original intent of this specific tool call. 

TODO:
Consider:
1. If the error suggests a specific provider is down, look for a similar tool from a different provider.
2. If the tool itself is failing due to some input issue, see if a different tool can pre-process or bypass the issue.
3. The alternative tool must be one of the available tools listed above.
4. It is possible that no alterantives exists and it is OK to say no suitable alternative exists
5. When you find an alternative, recheck to make sure it matches the goals of the failed action. 

Output a valid JSON object ONLY:
{{
  "action": "alternative_tool_name",
  "params": {{ ... }} // Parameters mapped to the alternative tool's expected format
}}
If no suitable alternative exists, return null."""


class RecoveryResult(BaseModel):
    """Result of a recovery attempt (retry/alternatives)."""

    success: bool
    action_taken: str = ""  # "retry", "alternative", "failed"
    result: Any = None
    attempts: int = 0
    error: str | None = None


class RollbackResult(BaseModel):
    """Result of a rollback operation."""

    success: bool
    compensated: list[str] = Field(default_factory=list)  # Record IDs
    failed: list[str] = Field(default_factory=list)  # Record IDs
    message: str = ""

    model_config = {"arbitrary_types_allowed": True}


class RecoveryManager:
    """Orchestrates retry, alternatives, and rollback logic.

    The "brain" of the compensation system. Handles:
    - Recording actions before execution
    - Marking actions complete/failed
    - Retry logic with configurable strategies
    - Alternative action fallback
    - Rollback with proper dependency ordering

    Example:
        manager = RecoveryManager(
            compensation_pairs={"book_flight": "cancel_flight"},
            alternative_map={"book_flight": ["book_flight_backup"]},
            retry_policy=RetryPolicy(max_retries=3),
        )

        # Record before execution
        record = manager.record_action("book_flight", {"dest": "NYC"})

        # Mark complete on success
        manager.mark_completed(record.id, result={"booking_id": "123"})

        # Or on failure, try recovery
        recovery = manager.recover(record.id, error)
        if not recovery.success:
            rollback = manager.rollback()
    """

    def __init__(
        self,
        compensation_pairs: CompensationPairs,
        alternative_map: AlternativeMap | None = None,
        retry_policy: RetryPolicy | None = None,
        retry_strategy: RetryStrategy | None = None,
        extraction_strategy: ExtractionStrategy | None = None,
        error_strategy: "ErrorStrategy | None" = None,
        action_executor: ActionExecutor | None = None,
        agent_id: str | None = None,
        infer_dependencies: bool = True,
        dynamic_matcher: Any | None = None,
        enable_tool_alternatives: bool = False,
        llm_model: str = "gpt-4o-mini",
    ):
        """Initialize recovery manager.

        Args:
            compensation_pairs: Maps tool names to compensation tools
            alternative_map: Maps tools to alternative tools to try
            retry_policy: Configuration for retry behavior
            retry_strategy: Strategy for retry decisions (overrides policy)
            extraction_strategy: Strategy for extracting compensation params
            error_strategy: Strategy for detecting errors in results
            action_executor: Executor for running tools
            agent_id: Identifier for multi-agent scenarios
            infer_dependencies: Auto-detect dependencies via data flow
            dynamic_matcher: Optional matcher to dynamically pair tools
        """
        self._compensation_pairs = compensation_pairs
        self._alternative_map = alternative_map or {}
        self._retry_policy = retry_policy or RetryPolicy()
        self._retry_strategy = retry_strategy or ExponentialBackoffStrategy(self._retry_policy)
        self._extraction_strategy = extraction_strategy or create_extraction_strategy()
        self._error_strategy = error_strategy
        self._action_executor = action_executor
        self._agent_id = agent_id
        self._infer_dependencies = infer_dependencies
        self._dynamic_matcher = dynamic_matcher
        self._enable_tool_alternatives = enable_tool_alternatives
        self._llm_model = llm_model
        self._llm_client: Any = None  # Lazy-loaded for tool alternative LLM calls
        self._log = TransactionLog()
        self._failure_context = FailureContext()

    @property
    def log(self) -> TransactionLog:
        """Access the transaction log."""
        return self._log

    @property
    def compensation_pairs(self) -> CompensationPairs:
        """Get compensation pair mappings."""
        return self._compensation_pairs

    @property
    def failure_context(self) -> FailureContext:
        """Access the failure context for cumulative failure tracking."""
        return self._failure_context

    def get_failure_summary(self) -> str:
        """Get cumulative failure context summary for LLM.

        Returns:
            Human-readable summary of all failed attempts, suitable for
            including in error messages to help the LLM make informed
            decisions about what to try next.
        """
        return self._failure_context.get_summary()

    def is_compensatable(self, action: str) -> bool:
        """Check if an action has a compensation pair or can be dynamically mapped."""
        if self._dynamic_matcher:
            return True
        return action in self._compensation_pairs

    def record_action(self, action: str, params: dict[str, Any]) -> ActionRecord:
        """Record an action before execution.

        Args:
            action: Name of the tool/action
            params: Parameters passed to the action

        Returns:
            Created ActionRecord with PENDING status
        """
        compensator = self._compensation_pairs.get(action)
        depends_on = self._infer_action_dependencies(params) if self._infer_dependencies else []

        record = ActionRecord(
            action=action,
            params=params,
            status=ActionStatus.PENDING,
            compensator=compensator,
            depends_on=depends_on,
            agent_id=self._agent_id,
        )
        self._log.add(record)
        logger.debug(f"Recorded action {action} with ID {record.id}")
        return record

    def mark_completed(self, record_id: str, result: Any) -> None:
        """Mark an action as successfully completed.

        Args:
            record_id: ID of the action record
            result: Result returned by the action
        """
        self._log.update(record_id, status=ActionStatus.COMPLETED, result=result)
        logger.debug(f"Marked action {record_id} as COMPLETED")

    def mark_failed(self, record_id: str, error: str | None = None) -> None:
        """Mark an action as failed.

        Args:
            record_id: ID of the action record
            error: Error message
        """
        result = {"error": error} if error else None
        self._log.update(record_id, status=ActionStatus.FAILED, result=result)
        logger.debug(f"Marked action {record_id} as FAILED: {error}")

    def _infer_action_dependencies(self, params: dict[str, Any]) -> list[str]:
        """Infer dependencies by matching params to previous results."""
        param_values = extract_all_values(params)
        if not param_values:
            return []

        dependencies = []
        for record_id, record in self._log.snapshot().items():
            if record.status != ActionStatus.COMPLETED:
                continue
            if record.result is None:
                continue

            result_values = extract_all_values(record.result)
            if param_values & result_values:  # Set intersection
                dependencies.append(record_id)

        return dependencies

    def recover(
        self,
        record_id: str,
        error: Exception | str,
        execute_fn: Any | None = None,
    ) -> RecoveryResult:
        """Attempt recovery via retry or alternatives.

        Args:
            record_id: ID of the failed action record
            error: The error that occurred
            execute_fn: Optional function to execute actions

        Returns:
            RecoveryResult indicating success/failure
        """
        record = self._log.get(record_id)
        if not record:
            return RecoveryResult(success=False, error=f"Record {record_id} not found")

        # Record this failed attempt for Strategic Context Preservation
        error_str = str(error)
        is_permanent = is_likely_permanent(error_str)
        self._failure_context.record_attempt(
            action=record.action,
            params=record.params,
            error=error_str,
            is_permanent=is_permanent,
        )

        # Try retries first
        context = RetryContext(
            error=error if isinstance(error, Exception) else Exception(error),
            attempt=1,
            action=record.action,
            params=record.params,
        )
        #Remove Prompt TODO222
        while self._retry_strategy.should_retry(context):
            delay = self._retry_strategy.get_delay(context)
            logger.info(f"Retrying {record.action} after {delay:.2f}s (attempt {context.attempt})")
            time.sleep(delay)

            try:
                result = self._execute_action(record.action, record.params, execute_fn)
                self.mark_completed(record_id, result)
                return RecoveryResult(
                    success=True,
                    action_taken="retry",
                    result=result,
                    attempts=context.attempt,
                )
            except Exception as e:
                context.error = e
                context.attempt += 1

        # Try static alternatives
        alternatives = self._alternative_map.get(record.action, [])
        for alt_action in alternatives:
            logger.info(f"Trying alternative: {alt_action}")
            try:
                result = self._execute_action(alt_action, record.params, execute_fn)
                # Update record with alternative action
                self._log.update(record_id, action=alt_action, status=ActionStatus.COMPLETED, result=result)
                return RecoveryResult(
                    success=True,
                    action_taken="alternative",
                    result=result,
                    attempts=context.attempt,
                )
            except Exception:
                continue

        # Try LLM-based tool alternative discovery (if enabled)
        if self._enable_tool_alternatives:
            llm_alt = self._find_tool_alternative(record.action, record.params, error_str)
            if llm_alt:
                alt_action = llm_alt.get("action")
                alt_params = llm_alt.get("params", record.params)
                if alt_action:
                    logger.info(f"[TOOL_ALT] Trying LLM-suggested alternative: {alt_action}")
                    try:
                        result = self._execute_action(alt_action, alt_params, execute_fn)
                        self._log.update(
                            record_id, action=alt_action,
                            status=ActionStatus.COMPLETED, result=result,
                        )
                        return RecoveryResult(
                            success=True,
                            action_taken="llm_alternative",
                            result=result,
                            attempts=context.attempt,
                        )
                    except Exception as e:
                        logger.warning(f"[TOOL_ALT] LLM alternative {alt_action} also failed: {e}")

        return RecoveryResult(
            success=False,
            action_taken="failed",
            attempts=context.attempt,
            error=str(error),
        )

    def _execute_action(
        self, action: str, params: dict[str, Any], execute_fn: Any | None
    ) -> Any:
        """Execute an action using provided executor or function."""
        if execute_fn:
            return execute_fn(action, params)
        if self._action_executor:
            return self._action_executor.execute(action, params)
        raise RuntimeError("No executor available")

    def rollback(self, failed_record_id: str | None = None) -> RollbackResult:
        """Execute rollback for completed actions.

        Args:
            failed_record_id: Optional ID of the record that triggered rollback

        Returns:
            RollbackResult with compensation details
        """
        plan = self._log.get_rollback_plan(
            agent_id=self._agent_id,
            include_unmapped=self._dynamic_matcher is not None,
        )
        if not plan:
            return RollbackResult(success=True, message="No actions to rollback")

        # Dynamic Matching Phase
        if self._dynamic_matcher:
            unmapped_actions = list({r.action for r in plan if not self._compensation_pairs.get(r.action)})
            if unmapped_actions:
                logger.info(f"[DYNAMIC] Invoking LLM matcher for {len(unmapped_actions)} unmapped actions: {unmapped_actions}")
                new_pairs = self._dynamic_matcher.match_batch(unmapped_actions)
                logger.info(f"[DYNAMIC] LLM matcher returned: {new_pairs}")
                if new_pairs:
                    self._compensation_pairs.update(new_pairs)
                    logger.info(f"[DYNAMIC] Updated compensation pairs: {self._compensation_pairs}")
                else:
                    logger.warning(f"[DYNAMIC] LLM matcher returned empty mapping!")
            else:
                logger.info(f"[DYNAMIC] All {len(plan)} actions already have static mappings")

        compensated: list[str] = []
        failed: list[str] = []

        for record in plan:
            # Sync compensator from dict if we dynamically discovered it
            record.compensator = self._compensation_pairs.get(record.action)
            logger.debug(f"[ROLLBACK] Processing: {record.action} compensator={record.compensator}")
            if not record.compensator:
                continue

            try:
                comp_params = self._extract_compensation_params(record)
                logger.debug(f"[ROLLBACK] Executing: {record.compensator}({comp_params})")
                self._execute_compensation(record.compensator, comp_params)
                self._log.mark_compensated(record.id)
                compensated.append(record.id)
                logger.info(f"[ROLLBACK] Compensated {record.action} with {record.compensator}")
            except Exception as e:
                failed.append(record.id)
                logger.error(f"[ROLLBACK] Compensation failed for {record.action}: {e}")
                if len(failed) > 0 and len(compensated) == 0:
                    # First compensation failed - critical
                    raise CriticalFailure(
                        f"Compensation failed immediately: {e}",
                        context={"record_id": record.id, "action": record.action},
                    ) from e

        success = len(failed) == 0
        if not success:
            raise RollbackFailure(
                f"Partial rollback: {len(compensated)} succeeded, {len(failed)} failed",
                failed_records=failed,
                compensated_records=compensated,
            )

        return RollbackResult(
            success=True,
            compensated=compensated,
            failed=failed,
            message=f"Rolled back {len(compensated)} actions",
        )

    def _extract_compensation_params(self, record: ActionRecord) -> dict[str, Any]:
        """Extract parameters for compensation tool."""
        try:
            return self._extraction_strategy.extract(
                result=record.result,
                original_params=record.params,
                tool_name=record.action,
            ) or {}
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract compensation params for {record.action}",
                tool_name=record.action,
                result=record.result,
            ) from e

    def _execute_compensation(self, action: str, params: dict[str, Any]) -> Any:
        """Execute a compensation action."""
        if self._action_executor:
            return self._action_executor.execute(action, params)
        raise RuntimeError("No executor available for compensation")

    def _find_tool_alternative(
        self, action: str, params: dict[str, Any], error: str,
    ) -> dict[str, Any] | None:
        """Find an alternative tool using the TOOL_ALTERNATIVE_PROMPT.

        Only called when enable_tool_alternatives is True.
        Uses LLM to analyze the failure and suggest an alternative tool
        from the available tools list.

        Args:
            action: The failed tool name
            params: Parameters that were passed to the failed tool
            error: The error message from the failure

        Returns:
            Dict with 'action' and 'params' keys if alternative found,
            None if no suitable alternative exists or feature is disabled.
        """
        if not self._enable_tool_alternatives:
            return None

        # Build available tools list from compensation pairs and alternative map
        available_tools = set(self._compensation_pairs.keys())
        available_tools.update(self._compensation_pairs.values())
        for alts in self._alternative_map.values():
            available_tools.update(alts)
        # Remove the failed action itself
        available_tools.discard(action)

        if not available_tools:
            logger.debug(f"[TOOL_ALT] No available tools to suggest as alternative for {action}")
            return None

        tools_list = "\n".join(f"  - {t}" for t in sorted(available_tools))

        prompt = TOOL_ALTERNATIVE_PROMPT.format(
            action=action,
            params=params,
            error=error,
            tools_list=tools_list,
        )

        logger.info(f"[TOOL_ALT] Querying LLM for alternative to {action}")
        logger.debug(f"[TOOL_ALT] Prompt:\n{prompt}")

        try:
            response_text = self._call_llm(prompt)
            return self._parse_alternative_response(response_text)
        except Exception as e:
            logger.warning(f"[TOOL_ALT] LLM call failed: {e}")
            return None

    def _get_llm_client(self) -> Any:
        """Lazy-load the LLM client for tool alternative discovery."""
        if self._llm_client is not None:
            return self._llm_client

        model_lower = self._llm_model.lower()

        if any(name in model_lower for name in ["gpt", "o1", "text-"]):
            try:
                from openai import OpenAI
                self._llm_client = ("openai", OpenAI())
            except ImportError as e:
                raise ImportError(
                    "OpenAI package required for tool alternatives. "
                    "Install with: pip install openai"
                ) from e
        elif "claude" in model_lower:
            try:
                from anthropic import Anthropic
                self._llm_client = ("anthropic", Anthropic())
            except ImportError as e:
                raise ImportError(
                    "Anthropic package required for tool alternatives. "
                    "Install with: pip install anthropic"
                ) from e
        elif any(name in model_lower for name in ["gemini", "models/"]):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._llm_client = ("google", ChatGoogleGenerativeAI(
                    model=self._llm_model, temperature=0.0,
                    max_retries=1, timeout=30,
                ))
            except ImportError as e:
                raise ImportError(
                    "langchain-google-genai required for tool alternatives. "
                    "Install with: pip install langchain-google-genai"
                ) from e
        else:
            # Default to OpenAI-compatible
            try:
                from openai import OpenAI
                self._llm_client = ("openai", OpenAI())
            except ImportError as e:
                raise ImportError(
                    "OpenAI package required for tool alternatives. "
                    "Install with: pip install openai"
                ) from e

        return self._llm_client

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return response text."""
        provider, client = self._get_llm_client()

        if provider == "openai":
            response = client.chat.completions.create(
                model=self._llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        elif provider == "anthropic":
            response = client.messages.create(
                model=self._llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        elif provider == "google":
            response = client.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _parse_alternative_response(self, response: str) -> dict[str, Any] | None:
        """Parse the LLM response for tool alternative suggestion.

        Returns:
            Dict with 'action' and 'params' if valid alternative found,
            None if LLM returned null or unparseable response.
        """
        import json as _json
        import re as _re

        response = response.strip()
        if not response or response.lower() == "null":
            logger.debug("[TOOL_ALT] LLM returned null — no alternative")
            return None

        # Remove markdown code blocks
        if response.startswith("```"):
            lines = response.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            response = "\n".join(lines).strip()

        # Try direct JSON parse
        try:
            parsed = _json.loads(response)
            if parsed is None:
                return None
            if isinstance(parsed, dict) and "action" in parsed:
                logger.info(f"[TOOL_ALT] LLM suggested alternative: {parsed['action']}")
                return parsed
        except _json.JSONDecodeError:
            pass

        # Try to find JSON object in response
        match = _re.search(r'\{.*\}', response, _re.DOTALL)
        if match:
            try:
                parsed = _json.loads(match.group())
                if isinstance(parsed, dict) and "action" in parsed:
                    logger.info(f"[TOOL_ALT] LLM suggested alternative: {parsed['action']}")
                    return parsed
            except _json.JSONDecodeError:
                pass

        logger.debug(f"[TOOL_ALT] Could not parse LLM response: {response[:200]}")
        return None

    def clear(self) -> None:
        """Clear the transaction log and failure context."""
        self._log.clear(agent_id=self._agent_id)
        self._failure_context.clear()

    def add_compensation_pair(self, forward: str, compensator: str) -> None:
        """Add a compensation pair at runtime.

        Args:
            forward: Name of the forward action
            compensator: Name of the compensation action
        """
        self._compensation_pairs[forward] = compensator

    def remove_compensation_pair(self, forward: str) -> bool:
        """Remove a compensation pair.

        Args:
            forward: Name of the forward action

        Returns:
            True if removed, False if not found
        """
        if forward in self._compensation_pairs:
            del self._compensation_pairs[forward]
            return True
        return False
