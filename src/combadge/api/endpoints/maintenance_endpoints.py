"""
Maintenance Endpoints for ComBadge Fleet API Client

Handles all maintenance-related API operations including scheduling,
tracking, parts management, and service history.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date

from .base_endpoint import BaseEndpoint, EndpointError


class MaintenanceEndpoints(BaseEndpoint):
    """
    Maintenance management API endpoints.
    
    Provides methods for:
    - Maintenance appointment scheduling and management
    - Service history tracking
    - Parts inventory and ordering
    - Technician assignment and scheduling
    - Maintenance reporting and analytics
    """
    
    def _get_base_path(self) -> str:
        """Return the base API path for maintenance endpoints"""
        return '/api/maintenance'
    
    def schedule_maintenance(
        self,
        vehicle_id: str,
        maintenance_type: str,
        requested_date: date,
        priority: str = 'normal',
        description: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        preferred_technician: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a maintenance appointment
        
        Args:
            vehicle_id: Unique vehicle identifier
            maintenance_type: Type of maintenance service
            requested_date: Preferred date for service
            priority: Service priority ('low', 'normal', 'high', 'urgent', 'emergency')
            description: Detailed description of maintenance needs
            estimated_duration: Estimated service time in hours
            preferred_technician: Requested technician ID or name
            
        Returns:
            Scheduled maintenance appointment details
        """
        appointment_data = {
            'vehicle_id': vehicle_id,
            'maintenance_type': maintenance_type,
            'requested_date': requested_date.isoformat(),
            'priority': priority
        }
        
        if description:
            appointment_data['description'] = description
        if estimated_duration:
            appointment_data['estimated_duration'] = estimated_duration
        if preferred_technician:
            appointment_data['preferred_technician'] = preferred_technician
        
        try:
            result = self._create_resource(appointment_data, additional_path='appointments')
            self._log_operation('schedule_maintenance', 
                              appointment_id=result.get('appointment_id'),
                              vehicle_id=vehicle_id)
            return result
        except Exception as e:
            self._handle_request_error(e, 'schedule_maintenance', 
                                     vehicle_id=vehicle_id, 
                                     maintenance_type=maintenance_type)
    
    def get_maintenance_appointment(self, appointment_id: str) -> Dict[str, Any]:
        """
        Get details of a specific maintenance appointment
        
        Args:
            appointment_id: Unique appointment identifier
            
        Returns:
            Complete appointment information
        """
        return self._get_resource(appointment_id, additional_path='appointments', use_cache=True)
    
    def update_maintenance_appointment(
        self,
        appointment_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update maintenance appointment details
        
        Args:
            appointment_id: Unique appointment identifier
            updates: Fields to update
            
        Returns:
            Updated appointment data
        """
        return self._update_resource(appointment_id, updates, 
                                   additional_path='appointments', method='PATCH')
    
    def cancel_maintenance_appointment(
        self,
        appointment_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a maintenance appointment
        
        Args:
            appointment_id: Unique appointment identifier
            cancellation_reason: Reason for cancellation
            
        Returns:
            Cancellation confirmation
        """
        cancel_data = {'status': 'cancelled'}
        if cancellation_reason:
            cancel_data['cancellation_reason'] = cancellation_reason
        
        return self._update_resource(appointment_id, cancel_data, 
                                   additional_path='appointments', method='PATCH')
    
    def list_maintenance_appointments(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 50,
        sort_by: str = 'requested_date',
        sort_order: str = 'asc'
    ) -> Dict[str, Any]:
        """
        List maintenance appointments with filtering
        
        Args:
            filters: Filtering criteria (status, vehicle_id, date_range, etc.)
            page: Page number for pagination
            limit: Number of results per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Paginated list of appointments
        """
        params = {
            'page': page,
            'limit': limit,
            'sort': f"{sort_by}:{sort_order}"
        }
        
        if filters:
            params.update(filters)
        
        return self._list_resources(additional_path='appointments', **params)
    
    def get_vehicle_maintenance_history(
        self,
        vehicle_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get maintenance history for a specific vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            start_date: Start date for history range
            end_date: End date for history range
            
        Returns:
            List of maintenance records
        """
        params = {'vehicle_id': vehicle_id}
        
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        result = self._list_resources(additional_path='history', **params)
        return result.get('items', result.get('history', []))
    
    def create_maintenance_record(
        self,
        vehicle_id: str,
        service_date: date,
        maintenance_type: str,
        technician: str,
        description: str,
        parts_used: Optional[List[Dict[str, Any]]] = None,
        labor_hours: Optional[float] = None,
        total_cost: Optional[float] = None,
        mileage_at_service: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a maintenance record for completed service
        
        Args:
            vehicle_id: Unique vehicle identifier
            service_date: Date service was performed
            maintenance_type: Type of maintenance performed
            technician: Technician who performed the service
            description: Description of work performed
            parts_used: List of parts used in the service
            labor_hours: Hours of labor
            total_cost: Total cost of service
            mileage_at_service: Vehicle mileage at time of service
            
        Returns:
            Created maintenance record
        """
        record_data = {
            'vehicle_id': vehicle_id,
            'service_date': service_date.isoformat(),
            'maintenance_type': maintenance_type,
            'technician': technician,
            'description': description
        }
        
        if parts_used:
            record_data['parts_used'] = parts_used
        if labor_hours:
            record_data['labor_hours'] = labor_hours
        if total_cost:
            record_data['total_cost'] = total_cost
        if mileage_at_service:
            record_data['mileage_at_service'] = mileage_at_service
        
        return self._create_resource(record_data, additional_path='records')
    
    def get_technician_schedule(
        self,
        technician_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get technician schedule for a date range
        
        Args:
            technician_id: Unique technician identifier
            start_date: Start date for schedule
            end_date: End date for schedule
            
        Returns:
            Technician schedule with appointments
        """
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        return self._get_resource(technician_id, additional_path='technicians/schedule', **params)
    
    def assign_technician(
        self,
        appointment_id: str,
        technician_id: str,
        estimated_start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Assign a technician to a maintenance appointment
        
        Args:
            appointment_id: Unique appointment identifier
            technician_id: Technician to assign
            estimated_start_time: Estimated start time for the work
            
        Returns:
            Assignment confirmation
        """
        assignment_data = {'assigned_technician': technician_id}
        
        if estimated_start_time:
            assignment_data['estimated_start_time'] = estimated_start_time.isoformat()
        
        return self._update_resource(appointment_id, assignment_data, 
                                   additional_path='appointments', method='PATCH')
    
    def get_available_technicians(
        self,
        requested_date: date,
        maintenance_type: Optional[str] = None,
        estimated_duration: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find available technicians for a specific date and service type
        
        Args:
            requested_date: Date for service
            maintenance_type: Type of maintenance (for skill matching)
            estimated_duration: Required service duration in hours
            
        Returns:
            List of available technicians
        """
        params = {'date': requested_date.isoformat()}
        
        if maintenance_type:
            params['maintenance_type'] = maintenance_type
        if estimated_duration:
            params['estimated_duration'] = estimated_duration
        
        result = self._list_resources(additional_path='technicians/available', **params)
        return result.get('items', result.get('technicians', []))
    
    def update_appointment_status(
        self,
        appointment_id: str,
        status: str,
        notes: Optional[str] = None,
        actual_start_time: Optional[datetime] = None,
        actual_end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a maintenance appointment
        
        Args:
            appointment_id: Unique appointment identifier
            status: New status ('scheduled', 'in_progress', 'completed', 'cancelled')
            notes: Status update notes
            actual_start_time: Actual start time (for in_progress status)
            actual_end_time: Actual completion time (for completed status)
            
        Returns:
            Updated appointment status
        """
        status_data = {'status': status}
        
        if notes:
            status_data['notes'] = notes
        if actual_start_time:
            status_data['actual_start_time'] = actual_start_time.isoformat()
        if actual_end_time:
            status_data['actual_end_time'] = actual_end_time.isoformat()
        
        return self._update_resource(appointment_id, status_data, 
                                   additional_path='appointments/status', method='PATCH')
    
    def get_parts_inventory(
        self,
        filters: Optional[Dict[str, Any]] = None,
        low_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get parts inventory information
        
        Args:
            filters: Filtering criteria (part_type, manufacturer, etc.)
            low_stock_only: Only return items with low stock levels
            
        Returns:
            List of parts in inventory
        """
        params = filters or {}
        
        if low_stock_only:
            params['low_stock'] = True
        
        result = self._list_resources(additional_path='parts', **params)
        return result.get('items', result.get('parts', []))
    
    def order_parts(
        self,
        parts_order: List[Dict[str, Any]],
        vendor: Optional[str] = None,
        urgency: str = 'normal'
    ) -> Dict[str, Any]:
        """
        Order parts for maintenance operations
        
        Args:
            parts_order: List of parts to order with quantities
            vendor: Preferred vendor for the order
            urgency: Order urgency ('normal', 'urgent', 'emergency')
            
        Returns:
            Parts order confirmation
        """
        order_data = {
            'parts': parts_order,
            'urgency': urgency,
            'order_date': datetime.now().isoformat()
        }
        
        if vendor:
            order_data['vendor'] = vendor
        
        return self._create_resource(order_data, additional_path='parts/orders')
    
    def get_maintenance_costs(
        self,
        vehicle_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: str = 'month'
    ) -> Dict[str, Any]:
        """
        Get maintenance cost analysis
        
        Args:
            vehicle_id: Specific vehicle ID (optional, for fleet-wide if not specified)
            start_date: Start date for cost analysis
            end_date: End date for cost analysis
            group_by: Grouping period ('day', 'week', 'month', 'year')
            
        Returns:
            Maintenance cost breakdown and analysis
        """
        params = {'group_by': group_by}
        
        if vehicle_id:
            params['vehicle_id'] = vehicle_id
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        return self._get_resource('costs', additional_path='reports', **params)
    
    def get_maintenance_schedule(
        self,
        date_range: Optional[tuple] = None,
        vehicle_id: Optional[str] = None,
        technician_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get maintenance schedule overview
        
        Args:
            date_range: Tuple of (start_date, end_date) for schedule range
            vehicle_id: Filter by specific vehicle
            technician_id: Filter by specific technician
            
        Returns:
            Scheduled maintenance appointments
        """
        params = {}
        
        if date_range:
            start_date, end_date = date_range
            params['start_date'] = start_date.isoformat()
            params['end_date'] = end_date.isoformat()
        
        if vehicle_id:
            params['vehicle_id'] = vehicle_id
        if technician_id:
            params['technician_id'] = technician_id
        
        result = self._list_resources(additional_path='schedule', **params)
        return result.get('items', result.get('appointments', []))
    
    def create_preventive_maintenance_plan(
        self,
        vehicle_id: str,
        maintenance_items: List[Dict[str, Any]],
        schedule_type: str = 'mileage'  # or 'time'
    ) -> Dict[str, Any]:
        """
        Create a preventive maintenance plan for a vehicle
        
        Args:
            vehicle_id: Unique vehicle identifier
            maintenance_items: List of maintenance items with intervals
            schedule_type: Scheduling basis ('mileage' or 'time')
            
        Returns:
            Created maintenance plan
        """
        plan_data = {
            'vehicle_id': vehicle_id,
            'maintenance_items': maintenance_items,
            'schedule_type': schedule_type,
            'created_date': datetime.now().isoformat()
        }
        
        return self._create_resource(plan_data, additional_path='plans')
    
    def get_overdue_maintenance(self, urgency_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Get list of vehicles with overdue maintenance
        
        Args:
            urgency_threshold: Days overdue to consider urgent
            
        Returns:
            List of vehicles with overdue maintenance
        """
        params = {'urgency_threshold': urgency_threshold}
        
        result = self._list_resources(additional_path='overdue', **params)
        return result.get('items', result.get('overdue', []))
    
    def get_maintenance_analytics(
        self,
        start_date: date,
        end_date: date,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get maintenance analytics and KPIs
        
        Args:
            start_date: Start date for analytics
            end_date: End date for analytics
            metrics: Specific metrics to include
            
        Returns:
            Maintenance analytics dashboard data
        """
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        if metrics:
            params['metrics'] = ','.join(metrics)
        
        return self._get_resource('analytics', additional_path='reports', **params)