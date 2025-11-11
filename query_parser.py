"""
Query parser module for interpreting natural language queries.
Uses LLM via MCP to extract structured criteria from user input.
"""

import json
import os
from typing import Dict, Optional, Tuple
import re


class QueryParser:
    """Parses natural language queries into structured criteria."""
    
    def __init__(self, use_llm: bool = False, llm_api_key: Optional[str] = None, llm_model: str = "llama3.2:3b"):
        """
        Initialize the query parser.
        
        Args:
            use_llm: Whether to use LLM for parsing (requires MCP setup)
            llm_api_key: Optional API key for LLM service
            llm_model: Model name for Ollama (default: llama3.2:3b)
        """
        self.use_llm = use_llm
        self.llm_api_key = llm_api_key or os.getenv('OPENAI_API_KEY')
        self.llm_model = llm_model
    
    def parse_query(self, query: str) -> Dict:
        """
        Parse natural language query into structured criteria.
        
        Args:
            query: Natural language query string
        
        Returns:
            Dictionary with:
                - criteria: Dict of weights for different factors
                - location: Dict with area name and optional coordinates
                - constraints: Dict with distance constraints
        """
        if self.use_llm:
            return self._parse_with_llm(query)
        else:
            return self._parse_with_rules(query)
    
    def _parse_with_rules(self, query: str) -> Dict:
        """
        Parse query using rule-based approach (fallback).
        """
        query_lower = query.lower()
        
        # Initialize criteria weights
        criteria = {
            'quiet_workspace': 0.0,
            'wifi_quality': 0.0,
            'metro_proximity': 0.0,
            'grocery_proximity': 0.0,
        }
        
        # Detect quiet workspace requirement (improved keyword matching)
        quiet_keywords = ['quiet', 'workspace', 'work', 'remote', 'digital nomad', 'working', 'desk', 'office']
        if any(keyword in query_lower for keyword in quiet_keywords):
            # Increase weight if multiple keywords are present
            quiet_count = sum(1 for keyword in quiet_keywords if keyword in query_lower)
            criteria['quiet_workspace'] = min(0.4, 0.25 + (quiet_count * 0.05))
        
        # Detect Wi-Fi requirement (improved keyword matching)
        wifi_keywords = ['wifi', 'wi-fi', 'internet', 'connectivity', 'stable', 'reliable', 'high-speed', 'wireless']
        if any(keyword in query_lower for keyword in wifi_keywords):
            # Increase weight if multiple keywords are present
            wifi_count = sum(1 for keyword in wifi_keywords if keyword in query_lower)
            criteria['wifi_quality'] = min(0.4, 0.25 + (wifi_count * 0.05))
        
        # Detect metro/bus requirement
        transit_keywords = ['metro', 'subway', 'tube', 'bus', 'transit', 'public transport', 'train', 'station']
        if any(keyword in query_lower for keyword in transit_keywords):
            criteria['metro_proximity'] = 0.25
        
        # Detect grocery requirement (improved keyword matching)
        grocery_keywords = ['grocery', 'supermarket', 'store', 'shopping', 'market', 'grocery store', 'grocery stores']
        if any(keyword in query_lower for keyword in grocery_keywords):
            # Increase weight if "within X km" is mentioned (stronger requirement)
            if 'within' in query_lower or 'less than' in query_lower:
                criteria['grocery_proximity'] = 0.3
            else:
                criteria['grocery_proximity'] = 0.2
        
        # Extract location
        location = self._extract_location(query)
        
        # Extract distance constraints
        constraints = self._extract_constraints(query)
        
        # Normalize weights if any are set
        total_weight = sum(criteria.values())
        if total_weight > 0:
            # Normalize to sum to 1.0
            for key in criteria:
                criteria[key] = criteria[key] / total_weight
        
        return {
            'criteria': criteria,
            'location': location,
            'constraints': constraints
        }
    
    def _parse_with_llm(self, query: str) -> Dict:
        """
        Parse query using LLM via MCP (if available).
        Falls back to rule-based parsing if LLM fails.
        """
        try:
            from mcp_server import MCPServer
            # Use Ollama by default, fallback to OpenAI if API key is provided
            if self.llm_api_key:
                mcp = MCPServer(llm_type="openai", api_key=self.llm_api_key)
            else:
                mcp = MCPServer(llm_type="ollama", model=self.llm_model)
            # Quick timeout for LLM - fallback fast if slow
            result = mcp.parse_query_with_llm(query)
            return result
        except Exception as e:
            # Fast fallback - don't wait for slow LLM
            print(f"LLM parsing skipped ({type(e).__name__}), using fast rule-based parser")
            return self._parse_with_rules(query)
    
    def _extract_location(self, query: str) -> Dict:
        """Extract location information from query."""
        location = {}
        
        # Common city/area patterns
        # This is a simplified version - could be enhanced with geocoding
        query_lower = query.lower()
        
        # Check for common areas in London
        london_areas = [
            'westminster', 'camden', 'islington', 'hackney', 'tower hamlets',
            'southwark', 'lambeth', 'kensington', 'chelsea', 'shoreditch',
            'soho', 'covent garden', 'finsbury park', 'camberwell', 'rotherhithe',
            'london', 'central london', 'east london', 'west london', 'north london', 'south london'
        ]
        
        for area in london_areas:
            if area in query_lower:
                location['area'] = area
                break
        
        # Extract "near X" pattern (stop at common words like "with", "and", etc.)
        # Also handle "in X", "at X" patterns
        patterns = [
            r'near\s+([a-z\s]+?)(?:\s+with|\s+and|\s+that|\s+which|$)',
            r'in\s+([a-z\s]+?)(?:\s+with|\s+and|\s+that|\s+which|$)',
            r'at\s+([a-z\s]+?)(?:\s+with|\s+and|\s+that|\s+which|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                area = match.group(1).strip()
                # Remove trailing common words and property types
                area = re.sub(r'\s+(with|and|that|which|apartment|apartments|place|places|listing|listings)$', '', area)
                # Remove leading articles
                area = re.sub(r'^(the|a|an)\s+', '', area)
                if area and len(area) > 2:  # Ensure it's a meaningful area name
                    location['area'] = area.strip()
                    break
        
        return location
    
    def _extract_constraints(self, query: str) -> Dict:
        """Extract distance constraints from query."""
        constraints = {}
        query_lower = query.lower()
        
        # Extract distance (e.g., "within 1 km", "less than 2km")
        distance_patterns = [
            r'within\s+(\d+(?:\.\d+)?)\s*km',
            r'less\s+than\s+(\d+(?:\.\d+)?)\s*km',
            r'(\d+(?:\.\d+)?)\s*km',
        ]
        
        for pattern in distance_patterns:
            match = re.search(pattern, query_lower)
            if match:
                distance = float(match.group(1))
                if 'grocery' in query_lower or 'store' in query_lower:
                    constraints['max_grocery_distance'] = distance
                elif 'metro' in query_lower or 'bus' in query_lower:
                    constraints['max_metro_distance'] = distance
                else:
                    constraints['max_distance'] = distance
                break
        
        return constraints

