"""
Vehicle Endpoints for ComBadge Fleet API Client

Handles all vehicle-related API operations including CRUD operations,
status management, availability checking, and assignment operations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date

from .base_endpoint import BaseEndpoint, EndpointError


class VehicleEndpoints(BaseEndpoint):
    """
    Vehicle management API endpoints.
    
    Provides methods for:
    - Vehicle CRUD operations
    - Vehicle status and assignment management
    - Availability checking and filtering
    - Vehicle utilization and reporting
    """
    
    def _get_base_path(self) -> str:
        """Return the base API path for vehicle endpoints"""
        return '/api/vehicles'
    
    def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new vehicle in the fleet
        
        Args:
            vehicle_data: Vehicle information including make, model, year, VIN, etc.
            
        Returns:
            Created vehicle data with assigned ID
            
        Raises:
            EndpointError: If required fields are missing
            APIError: If the API request fails
        """
        required_fields = ['make', 'model', 'year', 'vin', 'license_plate']
        self._validate_required_params(vehicle_data, required_fields)
        
        try:
            result = self._create_resource(vehicle_data)
            self._log_operation('create_vehicle', vehicle_id=result.get('vehicle_id'))
            return result
        except Exception as e:
            self._handle_request_error(e, 'create_vehicle', vehicle_data=vehicle_data)
    
    def get_vehicle(self, vehicle_id: str, include_details: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about a specific vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            include_details: Whether to include detailed status and assignment info
            
        Returns:
            Complete vehicle information
        """
        params = {}
        if include_details:
            params['include'] = 'status,assignment,maintenance_history'
        
        return self._get_resource(vehicle_id, use_cache=True, **params)
    
    def update_vehicle(
        self,
        vehicle_id: str,
        updates: Dict[str, Any],
        partial_update: bool = True
    ) -> Dict[str, Any]:
        """
        Update vehicle information
        
        Args:
            vehicle_id: Unique vehicle identifier
            updates: Fields to update
            partial_update: Whether to use PATCH (True) or PUT (False)
            
        Returns:
            Updated vehicle data
        """
        method = 'PATCH' if partial_update else 'PUT'
        return self._update_resource(vehicle_id, updates, method=method)
    
    def delete_vehicle(self, vehicle_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a vehicle from the fleet
        
        Args:
            vehicle_id: Unique vehicle identifier
            force: Whether to force deletion even if vehicle has dependencies
            
        Returns:
            Deletion confirmation
        """
        additional_path = '?force=true' if force else ''
        return self._delete_resource(vehicle_id, additional_path)
    
    def list_vehicles(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 50,
        sort_by: str = 'make',
        sort_order: str = 'asc'
    ) -> Dict[str, Any]:
        """
        List vehicles with optional filtering and pagination
        
        Args:
            filters: Filtering criteria (status, make, assigned_department, etc.)
            page: Page number for pagination
            limit: Number of results per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Paginated list of vehicles
        """
        params = {
            'page': page,
            'limit': limit,
            'sort': f"{sort_by}:{sort_order}"
        }
        
        if filters:
            params.update(filters)
        
        return self._list_resources(**params)
    
    def search_vehicles(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search vehicles by text query
        
        Args:
            query: Search query string
            search_fields: Specific fields to search in
            **kwargs: Additional parameters for list_vehicles
            
        Returns:
            Matching vehicles
        """
        params = {'search': query}
        
        if search_fields:
            params['search_fields'] = ','.join(search_fields)
        
        params.update(kwargs)
        return self.list_vehicles(**params)
    
    def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get current status of a vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            
        Returns:
            Current vehicle status information
        """
        return self._get_resource(vehicle_id, additional_path='status', use_cache=True)
    
    def update_vehicle_status(
        self,
        vehicle_id: str,
        status: str,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update vehicle status
        
        Args:
            vehicle_id: Unique vehicle identifier
            status: New status ('active', 'inactive', 'maintenance', 'retired')
            location: Current location
            notes: Status change notes
            
        Returns:
            Updated status information
        """
        status_data = {'status': status}
        
        if location:
            status_data['location'] = location
        if notes:
            status_data['notes'] = notes
        
        return self._update_resource(vehicle_id, status_data, additional_path='status')
    
    def assign_vehicle(
        self,
        vehicle_id: str,
        assigned_to: str,
        assignment_type: str = 'permanent',
        department: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Assign vehicle to a user or department
        
        Args:
            vehicle_id: Unique vehicle identifier
            assigned_to: User ID or email of assignee
            assignment_type: Type of assignment ('permanent', 'temporary', 'pool')
            department: Department for assignment
            start_date: Assignment start date
            end_date: Assignment end date (for temporary assignments)
            
        Returns:
            Assignment confirmation
        """
        assignment_data = {
            'assigned_to': assigned_to,
            'assignment_type': assignment_type
        }
        
        if department:
            assignment_data['department'] = department
        if start_date:
            assignment_data['start_date'] = start_date.isoformat()
        if end_date:
            assignment_data['end_date'] = end_date.isoformat()
        
        return self._update_resource(vehicle_id, assignment_data, additional_path='assignment')
    
    def unassign_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Remove current assignment from vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            
        Returns:
            Unassignment confirmation
        """
        return self._delete_resource(vehicle_id, additional_path='assignment')
    
    def get_vehicle_availability(
        self,
        vehicle_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        check_maintenance: bool = True
    ) -> Dict[str, Any]:
        """
        Check vehicle availability for a specific time period
        
        Args:
            vehicle_id: Unique vehicle identifier
            start_datetime: Start of availability window
            end_datetime: End of availability window
            check_maintenance: Whether to check maintenance schedule conflicts
            
        Returns:
            Availability information with conflicts
        """
        params = {
            'start_datetime': start_datetime.isoformat(),
            'end_datetime': end_datetime.isoformat(),
            'check_maintenance': check_maintenance
        }
        
        return self._get_resource(vehicle_id, additional_path='availability', **params)
    
    def find_available_vehicles(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all vehicles available for a specific time period
        
        Args:
            start_datetime: Start of availability window
            end_datetime: End of availability window
            filters: Additional filtering criteria
            
        Returns:
            List of available vehicles
        """
        params = {
            'start_datetime': start_datetime.isoformat(),
            'end_datetime': end_datetime.isoformat(),
            'available_only': True
        }
        
        if filters:
            params.update(filters)
        
        result = self._list_resources(additional_path='available', **params)
        
        # Extract just the vehicles list from paginated response
        return result.get('items', result.get('vehicles', []))
    
    def update_vehicle_mileage(
        self,
        vehicle_id: str,
        current_mileage: int,
        recorded_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update vehicle mileage reading
        
        Args:
            vehicle_id: Unique vehicle identifier
            current_mileage: Current odometer reading
            recorded_by: User who recorded the mileage
            notes: Additional notes about the reading
            
        Returns:
            Updated mileage information
        """
        mileage_data = {
            'current_mileage': current_mileage,
            'recorded_datetime': datetime.now().isoformat()
        }
        
        if recorded_by:
            mileage_data['recorded_by'] = recorded_by
        if notes:
            mileage_data['notes'] = notes
        
        return self._update_resource(vehicle_id, mileage_data, additional_path='mileage')
    
    def get_vehicle_utilization(
        self,
        vehicle_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get vehicle utilization statistics for a date range
        
        Args:
            vehicle_id: Unique vehicle identifier
            start_date: Start date for utilization report
            end_date: End date for utilization report
            
        Returns:
            Utilization statistics and metrics
        """
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        return self._get_resource(vehicle_id, additional_path='utilization', **params)
    
    def get_vehicles_by_department(self, department: str) -> List[Dict[str, Any]]:
        """
        Get all vehicles assigned to a specific department
        
        Args:
            department: Department name or ID
            
        Returns:
            List of vehicles assigned to the department
        """
        filters = {'assigned_department': department}
        result = self.list_vehicles(filters=filters, limit=self.max_page_size)
        
        # Get all pages if there are more results
        if result.get('pagination', {}).get('total_pages', 1) > 1:
            return self.get_all_pages(self.list_vehicles, filters=filters)
        
        return result.get('items', result.get('vehicles', []))
    
    def get_vehicles_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all vehicles with a specific status
        
        Args:
            status: Vehicle status to filter by
            
        Returns:
            List of vehicles with the specified status
        """
        filters = {'status': status}
        result = self.list_vehicles(filters=filters, limit=self.max_page_size)
        
        # Get all pages if there are more results
        if result.get('pagination', {}).get('total_pages', 1) > 1:
            return self.get_all_pages(self.list_vehicles, filters=filters)
        
        return result.get('items', result.get('vehicles', []))
    
    def get_vehicle_maintenance_schedule(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get upcoming maintenance schedule for a vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            
        Returns:
            Maintenance schedule information
        """
        return self._get_resource(vehicle_id, additional_path='maintenance/schedule', use_cache=True)
    
    def bulk_update_vehicles(
        self,
        updates: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Update multiple vehicles in batches
        
        Args:
            updates: List of vehicle updates, each containing 'vehicle_id' and update data
            batch_size: Number of vehicles to update per batch
            
        Returns:
            Bulk update results
        """
        try:
            endpoint = self._build_endpoint('bulk-update')
            
            # Process in batches
            all_results = []
            
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                batch_data = {'updates': batch}
                
                result = self.client.post(endpoint, data=batch_data)
                all_results.append(result)
            
            # Clear cache after bulk updates
            self._clear_cache()
            
            self._log_operation('bulk_update_vehicles', count=len(updates), batches=len(all_results))
            
            return {
                'total_updated': len(updates),
                'batches_processed': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            self._handle_request_error(e, 'bulk_update_vehicles', count=len(updates))
    
    def get_fleet_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the entire vehicle fleet
        
        Returns:
            Fleet summary with counts, status distribution, and key metrics
        """
        try:
            endpoint = self._build_endpoint('summary')
            result = self.client.get(endpoint)
            
            self._log_operation('get_fleet_summary')
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'get_fleet_summary')