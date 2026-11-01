import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class LLMToolMatcher:
    """Dynamically matches forward actions to their compensation tools.
    
    Uses an LLM and structured JSON mode to identify counter-tools when 
    static mappings are unavailable during rollback.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash", tools_metadata: List[Dict[str, Any]] = None):
        """Initialize the matcher.
        
        Args:
            model_name: The LLM model to use.
            tools_metadata: List of tool dicts containing 'name' and 'description'.
        """
        self.model_name = model_name
        self.tools_metadata = tools_metadata or []
        
    def match_batch(self, action_names: List[str]) -> Dict[str, str]:
        """Matches a batch of action names to their compensation tools.
        
        Args:
            action_names: List of tool names that need compensation.
            
        Returns:
            Dictionary mapping original action -> compensation tool.
            If an action shouldn't be compensated or has no match, maps to None.
        """
        if not action_names or not self.tools_metadata:
            return {}
            
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            tools_str = "\n".join([
                f"- Name: {t.get('name', 'Unknown')}\n  Description: {t.get('description', 'None')}"
                for t in self.tools_metadata
            ])
            
            prompt = f"""You are an expert resilience engineering system.
Your job is to identify the EXACT compensation tool (undo/rollback tool) for each given action.
If an action represents a state change (like scheduling, updating, booking), there is likely a tool to undo it.
If an action is read-only (get, list, search) or there is no matching tool, map it to null.

Available Tools:
{tools_str}

Actions that need compensation:
{json.dumps(action_names)}

Output a valid JSON object ONLY, where the keys are the Action names, and the values are the EXACT name of the compensation tool (or null).
Example output:
{{
  "schedule_job": "cancel_job",
  "search_catalog": null
}}
"""
            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.0,
                max_retries=1,
                timeout=30
            )
            # Use raw message to force formatting depending on model capabilities
            response = llm.invoke(prompt)
            
            content = response.content
            # Clean up potential markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            mapping = json.loads(content.strip())
            
            # Ensure safe dictionary return matching the requested keys
            final_mapping = {}
            for act in action_names:
                mapped_tool = mapping.get(act)
                # Verify that if it mapped something, that tool actually exists
                if mapped_tool and any(t.get('name') == mapped_tool for t in self.tools_metadata):
                    logger.info(f"LLM dynamically mapped {act} -> {mapped_tool}")
                    final_mapping[act] = mapped_tool
                else:
                    logger.debug(f"LLM determined no compensation for {act} (returned {mapped_tool})")
                    
            return final_mapping
            
        except Exception as e:
            logger.error(f"Dynamic LLM compensation matching failed: {e}")
            return {}
