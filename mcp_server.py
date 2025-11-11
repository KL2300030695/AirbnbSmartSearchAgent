"""
MCP (Model Context Protocol) server for LLM-based query interpretation.
Supports both local and hosted LLM services.
"""

import json
import os
from typing import Dict, Optional, Any
from query_parser import QueryParser


class MCPServer:
    """
    MCP server for LLM integration.
    Handles communication with LLM services for query parsing.
    """
    
    def __init__(self, llm_type: str = "ollama", api_key: Optional[str] = None, model: str = "llama3.2:3b"):
        """
        Initialize MCP server.
        
        Args:
            llm_type: Type of LLM service ('openai', 'local', 'ollama')
            api_key: API key for hosted services
            model: Model name for Ollama (default: llama3.2:3b)
        """
        self.llm_type = llm_type
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
    
    def parse_query_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query using LLM.
        
        Args:
            query: User query string
        
        Returns:
            Structured parsing result
        """
        if self.llm_type == "openai" and self.api_key:
            return self._parse_with_openai(query)
        elif self.llm_type == "ollama":
            return self._parse_with_ollama(query, model=self.model)
        elif self.llm_type == "local":
            return self._parse_with_local_llm(query)
        else:
            # Fallback to rule-based
            parser = QueryParser(use_llm=False)
            return parser.parse_query(query)
    
    def _parse_with_openai(self, query: str) -> Dict[str, Any]:
        """Parse query using OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            prompt = self._create_parsing_prompt(query)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # or gpt-4 for better results
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._format_llm_result(result)
        
        except Exception as e:
            print(f"Warning: LLM parsing failed ({e}), falling back to rule-based parser")
            parser = QueryParser(use_llm=False)
            return parser.parse_query(query)
    
    def _parse_with_ollama(self, query: str, model: str = "llama3.2:3b") -> Dict[str, Any]:
        """Parse query using Ollama (local LLM) - Software 3.0 with improved reasoning."""
        import requests
        
        prompt = self._create_parsing_prompt(query)
        system_prompt = self._get_system_prompt()
        response_text = None
        
        # Try chat API first (better for llama3.2)
        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 400,  # Reduced for faster response
                        "top_p": 0.9,
                    }
                },
                timeout=12  # Reasonable timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Handle chat API response format
                if "message" in response_data:
                    response_text = response_data["message"].get("content", "")
                else:
                    response_text = response_data.get("response", "")
            else:
                raise Exception(f"Chat API error: {response.status_code}")
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Fallback to generate API if chat API fails or times out
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": f"{system_prompt}\n\n{prompt}",
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 300,
                        }
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get("response", "")
                else:
                    raise Exception(f"Generate API error: {response.status_code}")
            except Exception as e2:
                raise Exception(f"Both APIs failed: {e2}")
        
        # Extract and parse JSON from response (response_text should be set by now)
        if not response_text:
            raise Exception("No response received from Ollama")
            
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            return self._format_llm_result(result)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON object
            import re
            # Try to find JSON object (handles nested braces)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return self._format_llm_result(result)
                except json.JSONDecodeError:
                    pass
            # If still fails, raise exception
            raise Exception(f"Could not parse JSON from Ollama response: {response_text[:200]}")
        
        except Exception as e:
            print(f"Warning: Ollama parsing failed ({type(e).__name__}: {str(e)[:100]}), falling back to rule-based parser")
            parser = QueryParser(use_llm=False)
            return parser.parse_query(query)
    
    def _parse_with_local_llm(self, query: str) -> Dict[str, Any]:
        """Parse query using local LLM (placeholder for custom implementation)."""
        # This would integrate with a local LLM service
        # For now, fall back to rule-based
        parser = QueryParser(use_llm=False)
        return parser.parse_query(query)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM - Software 3.0 with enhanced reasoning."""
        return """You are an expert AI agent specialized in parsing and understanding Airbnb search queries. 
You analyze natural language queries to extract structured search criteria with high accuracy.

Your task is to extract:
1. **Criteria weights** - How important each feature is (0.0 to 1.0)
   - quiet_workspace: Need for quiet space to work (keywords: quiet, workspace, work, remote, digital nomad, desk)
   - wifi_quality: Need for reliable internet (keywords: wifi, internet, stable, reliable, high-speed)
   - metro_proximity: Need to be near public transport (keywords: metro, tube, subway, bus, train, station)
   - grocery_proximity: Need to be near grocery stores (keywords: grocery, supermarket, store, shopping)

2. **Location** - Area or neighborhood name (e.g., "Westminster", "Islington")

3. **Constraints** - Distance requirements (e.g., "within 1 km", "less than 2km")

IMPORTANT RULES:
- Weights should reflect the importance mentioned in the query
- If a feature is explicitly mentioned, give it a higher weight (0.3-0.4)
- If a feature is strongly emphasized (e.g., "essential", "must have"), give it 0.4-0.5
- Weights should sum to approximately 1.0
- Set weight to 0.0 if criterion is NOT mentioned
- Extract location names accurately (London areas: Westminster, Islington, Camden, etc.)
- Parse distance constraints precisely (e.g., "within 1 km" → max_grocery_distance: 1.0)

Return ONLY valid JSON in this exact format:
{
  "criteria": {
    "quiet_workspace": <number 0-1>,
    "wifi_quality": <number 0-1>,
    "metro_proximity": <number 0-1>,
    "grocery_proximity": <number 0-1>
  },
  "location": {
    "area": "<string or null>"
  },
  "constraints": {
    "max_metro_distance": <number or null>,
    "max_grocery_distance": <number or null>
  }
}"""
    
    def _create_parsing_prompt(self, query: str) -> str:
        """Create prompt for query parsing - Software 3.0 optimized."""
        return f"""Parse this query: "{query}"

Extract: criteria weights (0-1), location area, distance constraints.
Return ONLY valid JSON."""
    
    def _format_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format LLM result to match expected structure."""
        # Ensure all required fields exist
        formatted = {
            'criteria': result.get('criteria', {}),
            'location': result.get('location', {}),
            'constraints': result.get('constraints', {})
        }
        
        # Normalize criteria weights
        criteria = formatted['criteria']
        total_weight = sum(criteria.values())
        if total_weight > 0:
            for key in criteria:
                criteria[key] = criteria[key] / total_weight
        
        return formatted

