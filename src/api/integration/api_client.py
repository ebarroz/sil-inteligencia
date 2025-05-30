"""
Generic API Client for SIL Predictive System

This module provides a flexible and reusable API client for integrating with
external measurement systems (thermography, oil analysis, vibration).

Features:
- Configurable authentication methods (API Key, Bearer Token, OAuth2)
- Automatic retry with exponential backoff
- Rate limiting support
- Response caching
- Comprehensive error handling
- Logging for debugging and auditing
"""

import requests
import time
import logging
import json
from typing import Dict, Any, Optional, Union, List, Callable
from datetime import datetime, timedelta
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sil_api_client')

class APIClient:
    """
    Generic API client for external system integration.
    
    This class handles common API interaction patterns including:
    - Authentication
    - Request retries
    - Rate limiting
    - Error handling
    - Response parsing
    """
    
    def __init__(
        self,
        base_url: str,
        auth_type: str = None,
        auth_credentials: Dict[str, str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        rate_limit: int = 60,  # requests per minute
        verify_ssl: bool = True
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the API (e.g., "https://api.example.com/v1")
            auth_type: Authentication type ("api_key", "bearer", "oauth2", None)
            auth_credentials: Dict containing auth credentials based on auth_type
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Initial delay between retries in seconds (will increase exponentially)
            rate_limit: Maximum number of requests per minute
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit = rate_limit
        self.verify_ssl = verify_ssl
        
        # Rate limiting tracking
        self._request_timestamps = []
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Configure authentication
        self._configure_auth()
        
        logger.info(f"Initialized API client for {base_url}")
    
    def _configure_auth(self) -> None:
        """Configure authentication based on auth_type."""
        if not self.auth_type:
            logger.info("No authentication configured")
            return
            
        if self.auth_type == "api_key":
            # API Key can be in header or query parameter
            if "header_name" in self.auth_credentials and "key" in self.auth_credentials:
                self.session.headers.update({
                    self.auth_credentials["header_name"]: self.auth_credentials["key"]
                })
                logger.info(f"Configured API Key authentication in header: {self.auth_credentials['header_name']}")
            elif "param_name" in self.auth_credentials and "key" in self.auth_credentials:
                # Will be added to query params in each request
                logger.info(f"Configured API Key authentication in query parameter: {self.auth_credentials['param_name']}")
            else:
                logger.warning("Incomplete API key credentials provided")
                
        elif self.auth_type == "bearer":
            if "token" in self.auth_credentials:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_credentials['token']}"
                })
                logger.info("Configured Bearer token authentication")
            else:
                logger.warning("Bearer token not provided")
                
        elif self.auth_type == "oauth2":
            # OAuth2 would typically require a more complex flow
            # This is a simplified version assuming we already have a token
            if "access_token" in self.auth_credentials:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_credentials['access_token']}"
                })
                logger.info("Configured OAuth2 authentication with provided access token")
            else:
                logger.warning("OAuth2 access token not provided")
        
        else:
            logger.warning(f"Unsupported authentication type: {self.auth_type}")
    
    def _check_rate_limit(self) -> None:
        """
        Check if we're exceeding the rate limit and wait if necessary.
        
        This implements a sliding window rate limiting approach.
        """
        if not self.rate_limit:
            return
            
        # Remove timestamps older than 1 minute
        current_time = time.time()
        self._request_timestamps = [ts for ts in self._request_timestamps 
                                   if current_time - ts < 60]
        
        # If we've hit the rate limit, wait until we can make another request
        if len(self._request_timestamps) >= self.rate_limit:
            oldest_timestamp = min(self._request_timestamps)
            sleep_time = 60 - (current_time - oldest_timestamp)
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Waiting {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        # Add current timestamp to the list
        self._request_timestamps.append(time.time())
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        files: Dict[str, Any] = None
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic and rate limiting.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Additional headers
            files: Files to upload
            
        Returns:
            Response object
        
        Raises:
            RequestException: If the request fails after all retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to query params if configured that way
        if (self.auth_type == "api_key" and 
            "param_name" in self.auth_credentials and 
            "key" in self.auth_credentials):
            params = params or {}
            params[self.auth_credentials["param_name"]] = self.auth_credentials["key"]
        
        # Check rate limit before making request
        self._check_rate_limit()
        
        # Retry logic
        retries = 0
        while retries <= self.max_retries:
            try:
                logger.debug(f"Making {method} request to {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=headers,
                    files=files,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                # Log request details for debugging
                logger.debug(f"Request: {method} {url}")
                if params:
                    logger.debug(f"Params: {params}")
                
                # Check if response indicates rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"Rate limited by server. Waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    retries += 1
                    continue
                
                # Check for server errors (5xx)
                if 500 <= response.status_code < 600:
                    if retries < self.max_retries:
                        wait_time = self.retry_delay * (2 ** retries)
                        logger.warning(f"Server error: {response.status_code}. Retrying in {wait_time} seconds")
                        time.sleep(wait_time)
                        retries += 1
                        continue
                
                # Log response status
                logger.debug(f"Response status: {response.status_code}")
                
                # Return response regardless of status code for caller to handle
                return response
                
            except (ConnectionError, Timeout) as e:
                if retries < self.max_retries:
                    wait_time = self.retry_delay * (2 ** retries)
                    logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time} seconds")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {str(e)}")
                    raise
        
        # This should not be reached due to the raise in the except block
        raise RequestException(f"Request failed after {self.max_retries} retries")
    
    def get(self, endpoint: str, params: Dict[str, Any] = None, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> requests.Response:
        """Make a POST request with JSON data."""
        return self._make_request("POST", endpoint, json_data=json_data, **kwargs)
    
    def put(self, endpoint: str, json_data: Dict[str, Any] = None, **kwargs) -> requests.Response:
        """Make a PUT request with JSON data."""
        return self._make_request("PUT", endpoint, json_data=json_data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a DELETE request."""
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def get_json(self, endpoint: str, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Make a GET request and return the JSON response.
        
        Raises:
            ValueError: If the response is not valid JSON
            RequestException: If the request fails or returns an error status
        """
        response = self.get(endpoint, params=params, **kwargs)
        
        if not response.ok:
            logger.error(f"Request failed with status {response.status_code}: {response.text}")
            response.raise_for_status()
        
        try:
            return response.json()
        except ValueError:
            logger.error(f"Invalid JSON response: {response.text}")
            raise ValueError(f"Invalid JSON response from {endpoint}")
    
    def get_paginated(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        page_param: str = "page",
        limit_param: str = "limit",
        limit: int = 100,
        max_pages: int = None,
        data_key: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all pages of paginated results.
        
        Args:
            endpoint: API endpoint
            params: Base query parameters
            page_param: Name of the page parameter
            limit_param: Name of the limit/per_page parameter
            limit: Number of items per page
            max_pages: Maximum number of pages to retrieve (None for all)
            data_key: Key in the response that contains the data array
            
        Returns:
            List of all items across all pages
        """
        params = params or {}
        params[limit_param] = limit
        params[page_param] = 1
        
        all_results = []
        page = 1
        
        while True:
            logger.info(f"Fetching page {page} from {endpoint}")
            response = self.get_json(endpoint, params=params)
            
            # Extract data based on the response structure
            if data_key:
                page_data = response.get(data_key, [])
            else:
                # Try to determine if this is an array response or has a standard data key
                if isinstance(response, list):
                    page_data = response
                else:
                    # Look for common data keys
                    for key in ['data', 'results', 'items', 'records']:
                        if key in response and isinstance(response[key], list):
                            page_data = response[key]
                            break
                    else:
                        logger.warning(f"Could not determine data key in response: {list(response.keys())}")
                        page_data = []
            
            all_results.extend(page_data)
            
            # Check if we've reached the end of pagination
            if not page_data or len(page_data) < limit:
                break
                
            # Check if we've reached max_pages
            if max_pages and page >= max_pages:
                logger.info(f"Reached maximum number of pages ({max_pages})")
                break
                
            # Increment page for next request
            page += 1
            params[page_param] = page
        
        logger.info(f"Retrieved {len(all_results)} total items from {endpoint}")
        return all_results
    
    def get_since(
        self,
        endpoint: str,
        since_datetime: datetime,
        datetime_param: str = "since",
        datetime_format: str = "%Y-%m-%dT%H:%M:%SZ",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get all results since a specific datetime.
        
        Args:
            endpoint: API endpoint
            since_datetime: Datetime to filter from
            datetime_param: Name of the datetime parameter
            datetime_format: Format string for the datetime parameter
            **kwargs: Additional arguments to pass to get_paginated
            
        Returns:
            List of all items since the specified datetime
        """
        params = kwargs.pop('params', {}) or {}
        params[datetime_param] = since_datetime.strftime(datetime_format)
        
        return self.get_paginated(endpoint, params=params, **kwargs)
