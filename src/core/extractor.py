"""
Microsoft Fabric Data Extraction Module

This module handles data extraction from Microsoft Fabric APIs including:
- Fabric Monitor Hub activities
- Power BI activity events  
- Workspace items and metadata
- Activity logs and metrics
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, timezone
import json
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import FabricAuthenticator
from .enrichment import (
    build_object_url,
    compute_duration_seconds,
    extract_user_from_metadata,
    infer_domain,
    infer_location,
    normalize_user,
)


class FabricDataExtractor:
    """Extracts monitoring data from Microsoft Fabric and Power BI APIs"""
    
    def __init__(self, authenticator: FabricAuthenticator):
        """
        Initialize the data extractor.
        
        Args:
            authenticator: Configured FabricAuthenticator instance
        """
        self.auth = authenticator
        self.logger = logging.getLogger(__name__)
        
        # API base URLs
        self.fabric_base_url = os.getenv("FABRIC_API_BASE_URL", "https://api.fabric.microsoft.com")
        self.powerbi_base_url = os.getenv("POWERBI_API_BASE_URL", "https://api.powerbi.com")
        self.api_version = os.getenv("FABRIC_API_VERSION", "v1")
        
        # Configure requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=int(os.getenv("MAX_RETRIES", "3")),
            backoff_factor=int(os.getenv("RETRY_BACKOFF_FACTOR", "2")),
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Request timeout
        self.timeout = int(os.getenv("API_REQUEST_TIMEOUT", "30"))

        # Simple in-memory caches for workspace metadata
        self._workspace_items_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._workspace_lookup: Dict[str, Dict[str, Any]] = {}
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Get list of all accessible Fabric workspaces.
        
        Returns:
            List of workspace dictionaries with id, name, and metadata
        """
        try:
            url = f"{self.fabric_base_url}/{self.api_version}/workspaces"
            headers = self.auth.get_fabric_headers()
            
            self.logger.info("Fetching Fabric workspaces")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            workspaces = data.get("value", [])
            
            self.logger.info(f"Retrieved {len(workspaces)} workspaces")
            return workspaces
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch workspaces: {str(e)}")
            raise
    
    def get_workspace_activities(self, workspace_id: str, start_date: datetime, 
                               end_date: datetime, activity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get activities for a specific workspace within date range.
        
        Args:
            workspace_id: Fabric workspace ID
            start_date: Start date for activity query
            end_date: End date for activity query  
            activity_types: Optional list of activity types to filter
            
        Returns:
            List of activity dictionaries
        """
        try:
            # Format dates for API (ISO 8601 format)
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            end_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            url = f"{self.fabric_base_url}/{self.api_version}/workspaces/{workspace_id}/activities"
            headers = self.auth.get_fabric_headers()
            
            params = {
                "startDateTime": start_str,
                "endDateTime": end_str
            }
            
            if activity_types:
                params["activityTypes"] = ",".join(activity_types)
            
            self.logger.info(f"Fetching activities for workspace {workspace_id} from {start_str} to {end_str}")
            response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            
            if response.status_code == 404:
                self.logger.warning(f"Activities endpoint not found for workspace {workspace_id} - using Power BI API fallback")
                return self._get_powerbi_activities_fallback(workspace_id, start_date, end_date, activity_types)
            
            response.raise_for_status()
            data = response.json()
            activities = data.get("value", [])
            
            self.logger.info(f"Retrieved {len(activities)} activities for workspace {workspace_id}")
            return activities
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch activities for workspace {workspace_id}: {str(e)}")
            # Try Power BI API as fallback
            return self._get_powerbi_activities_fallback(workspace_id, start_date, end_date, activity_types)
    
    def _get_powerbi_activities_fallback(self, workspace_id: str, start_date: datetime, 
                                       end_date: datetime, activity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fallback method to get activities using Power BI Admin API.
        """
        try:
            # Power BI Admin API for activity events requires ISO format with quotes
            start_str = f"'{start_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            end_str = f"'{end_date.strftime('%Y-%m-%dT%H:%M:%S')}'"
            
            url = f"{self.powerbi_base_url}/v1.0/myorg/admin/activityevents"
            headers = self.auth.get_powerbi_headers()
            
            params = {
                "startDateTime": start_str,
                "endDateTime": end_str
            }
            
            self.logger.info(f"Using Power BI Admin API fallback for workspace {workspace_id}")
            response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            all_activities = data.get("activityEventEntities", [])
            
            # Filter by workspace if specified
            if workspace_id:
                workspace_activities = [
                    activity for activity in all_activities 
                    if activity.get("WorkspaceId") == workspace_id
                ]
            else:
                workspace_activities = all_activities
            
            # Filter by activity types if specified
            if activity_types:
                workspace_activities = [
                    activity for activity in workspace_activities
                    if activity.get("Activity") in activity_types
                ]
            
            self.logger.info(f"Retrieved {len(workspace_activities)} activities via Power BI API")
            return workspace_activities
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Power BI API fallback also failed: {str(e)}")
            return []
    
    def get_daily_activities(self, date: datetime, workspace_ids: Optional[List[str]] = None, 
                           activity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get all activities for a specific date across specified workspaces.
        
        Args:
            date: Date to fetch activities for
            workspace_ids: Optional list of workspace IDs (if None, fetch from all accessible workspaces)
            activity_types: Optional list of activity types to filter
            
        Returns:
            List of all activities for the specified date
        """
        # Set up date range (full day)
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
        
        all_activities = []
        
        # Get workspaces to query
        if workspace_ids:
            all_workspaces = {ws["id"]: ws for ws in self.get_workspaces()}
            target_workspaces = [all_workspaces.get(ws_id, {"id": ws_id}) for ws_id in workspace_ids]
        else:
            # Get all accessible workspaces
            target_workspaces = self.get_workspaces()

        self._workspace_lookup = {ws.get("id"): ws for ws in target_workspaces if ws.get("id")}
        
        self.logger.info(f"Fetching activities for {len(target_workspaces)} workspaces on {date.strftime('%Y-%m-%d')}")
        
        # Fetch activities for each workspace
        for workspace in target_workspaces:
            workspace_id = workspace.get("id")
            if not workspace_id:
                continue
                
            try:
                activities = self.get_workspace_activities(
                    workspace_id=workspace_id,
                    start_date=start_date,
                    end_date=end_date,
                    activity_types=activity_types
                )
                
                item_lookup = self._get_workspace_items_lookup(workspace_id)

                # Add workspace info to each activity and enrich with metadata
                for activity in activities:
                    enriched = self._enrich_activity(activity, workspace_id, workspace)
                    if item_lookup:
                        self._attach_item_metadata(enriched, workspace_id, item_lookup)
                    all_activities.append(enriched)
                
            except Exception as e:
                self.logger.warning(f"Failed to fetch activities for workspace {workspace_id}: {str(e)}")
                continue
        
        self.logger.info(f"Total activities retrieved for {date.strftime('%Y-%m-%d')}: {len(all_activities)}")
        return all_activities
    
    def get_workspace_items(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all items (reports, datasets, etc.) in a workspace.
        
        Args:
            workspace_id: Fabric workspace ID
            
        Returns:
            List of workspace items
        """
        try:
            url = f"{self.fabric_base_url}/{self.api_version}/workspaces/{workspace_id}/items"
            headers = self.auth.get_fabric_headers()
            
            self.logger.info(f"Fetching items for workspace {workspace_id}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("value", [])
            
            self.logger.info(f"Retrieved {len(items)} items for workspace {workspace_id}")
            return items
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch items for workspace {workspace_id}: {str(e)}")
            return []

    # ------------------------------------------------------------------
    # Enrichment helpers
    # ------------------------------------------------------------------

    def _get_workspace_items_lookup(self, workspace_id: str) -> Dict[str, Dict[str, Any]]:
        """Return (and cache) workspace items keyed by item id."""
        if workspace_id in self._workspace_items_cache:
            return self._workspace_items_cache[workspace_id]

        try:
            items = self.get_workspace_items(workspace_id)
            lookup = {item.get("id"): item for item in items if item.get("id")}
            self._workspace_items_cache[workspace_id] = lookup
            return lookup
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning(f"Unable to cache workspace items for {workspace_id}: {exc}")
            self._workspace_items_cache[workspace_id] = {}
            return {}

    def _enrich_activity(self, activity: Dict[str, Any], workspace_id: str, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Attach workspace context, derived fields, and normalized values."""
        workspace_name = workspace.get("displayName") or workspace.get("name") or "Unknown"
        activity["_workspace_id"] = workspace_id
        activity["_workspace_name"] = workspace_name
        activity["_extraction_date"] = datetime.now().isoformat()
        activity.setdefault("WorkspaceId", workspace_id)
        activity.setdefault("WorkspaceName", workspace_name)

        # Derived identifiers and names
        item_id = self._extract_item_id(activity)
        if item_id:
            activity.setdefault("ItemId", item_id)

        if not activity.get("ItemName"):
            for key in ["ArtifactName", "ObjectName", "Name", "DatasetName", "ReportName"]:
                value = activity.get(key)
                if value:
                    activity["ItemName"] = value
                    break

        submitted_by = normalize_user(activity.get("SubmittedBy") or activity.get("UserId") or activity.get("UserKey"))
        if submitted_by:
            activity["SubmittedBy"] = submitted_by

        duration_seconds = compute_duration_seconds(activity)
        if duration_seconds is not None:
            activity["DurationSeconds"] = duration_seconds

        if not activity.get("ItemType"):
            fallback_type = activity.get("ArtifactType") or activity.get("ArtifactKind") or activity.get("ObjectType")
            if fallback_type:
                activity["ItemType"] = fallback_type

        # Domain/location heuristics
        domain_source = activity.get("ItemName") or workspace_name
        activity["Domain"] = activity.get("Domain") or infer_domain(domain_source)
        activity["Location"] = activity.get("Location") or infer_location(workspace)

        return activity

    def _attach_item_metadata(self, activity: Dict[str, Any], workspace_id: str, item_lookup: Dict[str, Dict[str, Any]]) -> None:
        """Merge workspace item metadata into the activity record."""
        item_id = activity.get("ItemId")
        metadata = item_lookup.get(item_id) if item_id else None
        if not metadata:
            return

        activity["ItemName"] = metadata.get("displayName") or activity.get("ItemName")
        activity["ItemType"] = metadata.get("type") or activity.get("ItemType")
        activity["ObjectUrl"] = activity.get("ObjectUrl") or build_object_url(workspace_id, item_id, activity.get("ItemType"))

        created_by = extract_user_from_metadata(metadata.get("createdByUser"))
        if created_by:
            activity["CreatedBy"] = created_by

        modified_by = extract_user_from_metadata(metadata.get("modifiedByUser"))
        if modified_by:
            activity["LastUpdatedBy"] = modified_by

        activity["Domain"] = activity.get("Domain") or infer_domain(metadata.get("displayName"))

    def _extract_item_id(self, activity: Dict[str, Any]) -> Optional[str]:
        """Look across multiple potential keys to find an item identifier."""
        candidate_keys = [
            "ItemId",
            "ArtifactId",
            "ObjectId",
            "ArtifactInstanceId",
            "DatasetId",
            "ReportId",
        ]
        for key in candidate_keys:
            value = activity.get(key)
            if value:
                return str(value)
        return None
    
    def test_api_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to Fabric and Power BI APIs.
        
        Returns:
            Dictionary with connectivity test results
        """
        results = {
            "fabric_api": False,
            "powerbi_api": False,
            "authentication": False
        }
        
        # Test authentication
        try:
            results["authentication"] = self.auth.validate_credentials()
        except Exception as e:
            self.logger.error(f"Authentication test failed: {str(e)}")
        
        # Test Fabric API
        try:
            workspaces = self.get_workspaces()
            results["fabric_api"] = len(workspaces) >= 0  # Even 0 workspaces means API is accessible
        except Exception as e:
            self.logger.error(f"Fabric API test failed: {str(e)}")
        
        # Test Power BI API
        try:
            url = f"{self.powerbi_base_url}/v1.0/myorg/groups"
            headers = self.auth.get_powerbi_headers()
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            results["powerbi_api"] = response.status_code == 200
        except Exception as e:
            self.logger.error(f"Power BI API test failed: {str(e)}")
        
        return results