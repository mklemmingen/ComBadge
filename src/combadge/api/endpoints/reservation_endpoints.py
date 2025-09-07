"""
Reservation Endpoints for ComBadge Fleet API Client

Handles all reservation-related API operations including booking,
modification, cancellation, and availability management.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta

from .base_endpoint import BaseEndpoint, EndpointError


class ReservationEndpoints(BaseEndpoint):
    """
    Reservation management API endpoints.
    
    Provides methods for:
    - Vehicle reservation booking and management
    - Availability checking and conflict resolution
    - Reservation approval workflows
    - Usage tracking and reporting
    - Calendar integration and scheduling
    """
    
    def _get_base_path(self) -> str:
        """Return the base API path for reservation endpoints"""
        return '/api/reservations'
    
    def create_reservation(
        self,
        vehicle_id: str,
        user_id: str,
        start_datetime: datetime,
        end_datetime: Optional[datetime] = None,
        duration_hours: Optional[float] = None,
        purpose: Optional[str] = None,
        destination: Optional[str] = None,
        passenger_count: int = 1,
        special_requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new vehicle reservation
        
        Args:
            vehicle_id: Unique vehicle identifier
            user_id: User making the reservation
            start_datetime: Reservation start time
            end_datetime: Reservation end time (alternative to duration_hours)
            duration_hours: Reservation duration in hours (alternative to end_datetime)
            purpose: Business purpose for the reservation
            destination: Primary destination
            passenger_count: Number of passengers including driver
            special_requirements: List of special equipment or needs
            
        Returns:
            Created reservation details
        """
        # Validate time parameters
        if not end_datetime and not duration_hours:
            raise EndpointError("Either end_datetime or duration_hours must be provided")
        
        if end_datetime and duration_hours:
            raise EndpointError("Provide either end_datetime or duration_hours, not both")
        
        # Calculate end_datetime if duration is provided
        if duration_hours and not end_datetime:
            end_datetime = start_datetime + timedelta(hours=duration_hours)
        
        reservation_data = {
            'vehicle_id': vehicle_id,
            'user_id': user_id,
            'start_datetime': start_datetime.isoformat(),
            'end_datetime': end_datetime.isoformat(),
            'passenger_count': passenger_count
        }
        
        if purpose:
            reservation_data['purpose'] = purpose
        if destination:
            reservation_data['destination'] = destination
        if special_requirements:
            reservation_data['special_requirements'] = special_requirements
        
        try:
            result = self._create_resource(reservation_data)
            self._log_operation('create_reservation', 
                              reservation_id=result.get('reservation_id'),
                              vehicle_id=vehicle_id, user_id=user_id)
            return result
        except Exception as e:
            self._handle_request_error(e, 'create_reservation', 
                                     vehicle_id=vehicle_id, user_id=user_id)
    
    def get_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """
        Get details of a specific reservation
        
        Args:
            reservation_id: Unique reservation identifier
            
        Returns:
            Complete reservation information
        """
        return self._get_resource(reservation_id, use_cache=True)
    
    def update_reservation(
        self,
        reservation_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update reservation details
        
        Args:
            reservation_id: Unique reservation identifier
            updates: Fields to update
            
        Returns:
            Updated reservation data
        """
        # Handle datetime fields in updates
        if 'start_datetime' in updates and isinstance(updates['start_datetime'], datetime):
            updates['start_datetime'] = updates['start_datetime'].isoformat()
        if 'end_datetime' in updates and isinstance(updates['end_datetime'], datetime):
            updates['end_datetime'] = updates['end_datetime'].isoformat()
        
        return self._update_resource(reservation_id, updates, method='PATCH')
    
    def cancel_reservation(
        self,
        reservation_id: str,
        cancellation_reason: Optional[str] = None,
        notify_stakeholders: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a reservation
        
        Args:
            reservation_id: Unique reservation identifier
            cancellation_reason: Reason for cancellation
            notify_stakeholders: Whether to send notifications
            
        Returns:
            Cancellation confirmation
        """
        cancel_data = {
            'status': 'cancelled',
            'cancelled_at': datetime.now().isoformat(),
            'notify_stakeholders': notify_stakeholders
        }
        
        if cancellation_reason:
            cancel_data['cancellation_reason'] = cancellation_reason
        
        return self._update_resource(reservation_id, cancel_data, method='PATCH')
    
    def list_reservations(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 50,
        sort_by: str = 'start_datetime',
        sort_order: str = 'asc'
    ) -> Dict[str, Any]:
        """
        List reservations with filtering and pagination
        
        Args:
            filters: Filtering criteria (user_id, vehicle_id, status, date_range, etc.)
            page: Page number for pagination
            limit: Number of results per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Paginated list of reservations
        """
        params = {
            'page': page,
            'limit': limit,
            'sort': f"{sort_by}:{sort_order}"
        }
        
        if filters:
            params.update(filters)
        
        return self._list_resources(**params)
    
    def check_availability(
        self,
        vehicle_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_reservation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check vehicle availability for a specific time period
        
        Args:
            vehicle_id: Unique vehicle identifier
            start_datetime: Start of requested time period
            end_datetime: End of requested time period
            exclude_reservation: Reservation ID to exclude from conflict check
            
        Returns:
            Availability status and conflicting reservations
        """
        params = {
            'vehicle_id': vehicle_id,
            'start_datetime': start_datetime.isoformat(),
            'end_datetime': end_datetime.isoformat()
        }
        
        if exclude_reservation:
            params['exclude'] = exclude_reservation
        
        try:
            endpoint = self._build_endpoint('availability')
            result = self.client.get(endpoint, params=params)
            
            self._log_operation('check_availability', vehicle_id=vehicle_id)
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'check_availability', vehicle_id=vehicle_id)
    
    def find_available_vehicles(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find available vehicles for a time period
        
        Args:
            start_datetime: Start of requested time period
            end_datetime: End of requested time period
            filters: Additional filtering criteria (vehicle_type, features, etc.)
            max_results: Maximum number of vehicles to return
            
        Returns:
            List of available vehicles with suitability scores
        """
        params = {
            'start_datetime': start_datetime.isoformat(),
            'end_datetime': end_datetime.isoformat(),
            'limit': max_results
        }
        
        if filters:
            params.update(filters)
        
        try:
            endpoint = self._build_endpoint('available-vehicles')
            result = self.client.get(endpoint, params=params)
            
            # Extract vehicles list from response
            vehicles = result.get('vehicles', result.get('items', []))
            
            self._log_operation('find_available_vehicles', count=len(vehicles))
            return vehicles
            
        except Exception as e:
            self._handle_request_error(e, 'find_available_vehicles')
    
    def get_user_reservations(
        self,
        user_id: str,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all reservations for a specific user
        
        Args:
            user_id: User identifier
            status: Filter by reservation status
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of user's reservations
        """
        filters = {'user_id': user_id}
        
        if status:
            filters['status'] = status
        if start_date:
            filters['start_date'] = start_date.isoformat()
        if end_date:
            filters['end_date'] = end_date.isoformat()
        
        result = self.list_reservations(filters=filters, limit=self.max_page_size)
        
        # Get all pages if there are more results
        if result.get('pagination', {}).get('total_pages', 1) > 1:
            return self.get_all_pages(self.list_reservations, filters=filters)
        
        return result.get('items', result.get('reservations', []))
    
    def get_vehicle_reservations(
        self,
        vehicle_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_cancelled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all reservations for a specific vehicle
        
        Args:
            vehicle_id: Vehicle identifier
            start_date: Start date for filtering
            end_date: End date for filtering
            include_cancelled: Whether to include cancelled reservations
            
        Returns:
            List of vehicle's reservations
        """
        filters = {'vehicle_id': vehicle_id}
        
        if start_date:
            filters['start_date'] = start_date.isoformat()
        if end_date:
            filters['end_date'] = end_date.isoformat()
        if not include_cancelled:
            filters['status'] = 'active,confirmed,in_progress,completed'
        
        result = self.list_reservations(filters=filters, limit=self.max_page_size)
        
        # Get all pages if there are more results
        if result.get('pagination', {}).get('total_pages', 1) > 1:
            return self.get_all_pages(self.list_reservations, filters=filters)
        
        return result.get('items', result.get('reservations', []))
    
    def extend_reservation(
        self,
        reservation_id: str,
        new_end_datetime: datetime,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extend an existing reservation
        
        Args:
            reservation_id: Unique reservation identifier
            new_end_datetime: New end time for the reservation
            reason: Reason for extension
            
        Returns:
            Updated reservation details
        """
        extension_data = {
            'end_datetime': new_end_datetime.isoformat(),
            'extension_requested_at': datetime.now().isoformat()
        }
        
        if reason:
            extension_data['extension_reason'] = reason
        
        return self._update_resource(reservation_id, extension_data, 
                                   additional_path='extend', method='PATCH')
    
    def start_reservation(
        self,
        reservation_id: str,
        actual_start_time: Optional[datetime] = None,
        starting_mileage: Optional[int] = None,
        fuel_level: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Mark a reservation as started (check-out)
        
        Args:
            reservation_id: Unique reservation identifier
            actual_start_time: Actual start time (defaults to now)
            starting_mileage: Vehicle mileage at start
            fuel_level: Fuel level at start (0.0 to 1.0)
            
        Returns:
            Updated reservation with check-out details
        """
        checkout_data = {
            'status': 'in_progress',
            'actual_start_time': (actual_start_time or datetime.now()).isoformat()
        }
        
        if starting_mileage:
            checkout_data['starting_mileage'] = starting_mileage
        if fuel_level is not None:
            checkout_data['starting_fuel_level'] = fuel_level
        
        return self._update_resource(reservation_id, checkout_data, 
                                   additional_path='start', method='PATCH')
    
    def end_reservation(
        self,
        reservation_id: str,
        actual_end_time: Optional[datetime] = None,
        ending_mileage: Optional[int] = None,
        fuel_level: Optional[float] = None,
        condition_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a reservation as completed (check-in)
        
        Args:
            reservation_id: Unique reservation identifier
            actual_end_time: Actual end time (defaults to now)
            ending_mileage: Vehicle mileage at end
            fuel_level: Fuel level at end (0.0 to 1.0)
            condition_notes: Notes about vehicle condition
            
        Returns:
            Updated reservation with check-in details
        """
        checkin_data = {
            'status': 'completed',
            'actual_end_time': (actual_end_time or datetime.now()).isoformat()
        }
        
        if ending_mileage:
            checkin_data['ending_mileage'] = ending_mileage
        if fuel_level is not None:
            checkin_data['ending_fuel_level'] = fuel_level
        if condition_notes:
            checkin_data['condition_notes'] = condition_notes
        
        return self._update_resource(reservation_id, checkin_data, 
                                   additional_path='end', method='PATCH')
    
    def request_approval(
        self,
        reservation_id: str,
        approval_reason: str,
        approver: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request approval for a reservation
        
        Args:
            reservation_id: Unique reservation identifier
            approval_reason: Reason why approval is needed
            approver: Specific person to request approval from
            
        Returns:
            Approval request details
        """
        approval_data = {
            'approval_status': 'pending',
            'approval_reason': approval_reason,
            'approval_requested_at': datetime.now().isoformat()
        }
        
        if approver:
            approval_data['requested_approver'] = approver
        
        return self._update_resource(reservation_id, approval_data, 
                                   additional_path='approval', method='PATCH')
    
    def approve_reservation(
        self,
        reservation_id: str,
        approver: str,
        approval_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a pending reservation
        
        Args:
            reservation_id: Unique reservation identifier
            approver: Person approving the reservation
            approval_notes: Notes from approver
            
        Returns:
            Updated reservation with approval status
        """
        approval_data = {
            'approval_status': 'approved',
            'approved_by': approver,
            'approved_at': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        if approval_notes:
            approval_data['approval_notes'] = approval_notes
        
        return self._update_resource(reservation_id, approval_data, 
                                   additional_path='approval', method='PATCH')
    
    def deny_reservation(
        self,
        reservation_id: str,
        denier: str,
        denial_reason: str
    ) -> Dict[str, Any]:
        """
        Deny a pending reservation
        
        Args:
            reservation_id: Unique reservation identifier
            denier: Person denying the reservation
            denial_reason: Reason for denial
            
        Returns:
            Updated reservation with denial status
        """
        denial_data = {
            'approval_status': 'denied',
            'denied_by': denier,
            'denied_at': datetime.now().isoformat(),
            'denial_reason': denial_reason,
            'status': 'cancelled'
        }
        
        return self._update_resource(reservation_id, denial_data, 
                                   additional_path='approval', method='PATCH')
    
    def get_pending_approvals(self, approver: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get reservations pending approval
        
        Args:
            approver: Filter by specific approver (optional)
            
        Returns:
            List of reservations pending approval
        """
        filters = {'approval_status': 'pending'}
        
        if approver:
            filters['requested_approver'] = approver
        
        result = self.list_reservations(filters=filters, limit=self.max_page_size)
        return result.get('items', result.get('reservations', []))
    
    def get_reservation_calendar(
        self,
        start_date: date,
        end_date: date,
        vehicle_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get calendar view of reservations
        
        Args:
            start_date: Start date for calendar
            end_date: End date for calendar
            vehicle_id: Filter by specific vehicle
            user_id: Filter by specific user
            
        Returns:
            Calendar data with reservations
        """
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'view': 'calendar'
        }
        
        if vehicle_id:
            params['vehicle_id'] = vehicle_id
        if user_id:
            params['user_id'] = user_id
        
        try:
            endpoint = self._build_endpoint('calendar')
            result = self.client.get(endpoint, params=params)
            
            self._log_operation('get_reservation_calendar')
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'get_reservation_calendar')
    
    def get_utilization_report(
        self,
        start_date: date,
        end_date: date,
        group_by: str = 'vehicle',
        include_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get reservation utilization report
        
        Args:
            start_date: Start date for report
            end_date: End date for report
            group_by: Grouping method ('vehicle', 'user', 'department', 'day')
            include_metrics: Specific metrics to include
            
        Returns:
            Utilization report data
        """
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'group_by': group_by
        }
        
        if include_metrics:
            params['metrics'] = ','.join(include_metrics)
        
        try:
            endpoint = self._build_endpoint('reports/utilization')
            result = self.client.get(endpoint, params=params)
            
            self._log_operation('get_utilization_report')
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'get_utilization_report')
    
    def create_recurring_reservation(
        self,
        base_reservation: Dict[str, Any],
        recurrence_pattern: Dict[str, Any],
        end_recurrence_date: date
    ) -> Dict[str, Any]:
        """
        Create a recurring reservation pattern
        
        Args:
            base_reservation: Base reservation data
            recurrence_pattern: Recurrence settings (frequency, days, etc.)
            end_recurrence_date: When to stop creating recurring reservations
            
        Returns:
            Created recurring reservation series
        """
        recurring_data = {
            'base_reservation': base_reservation,
            'recurrence_pattern': recurrence_pattern,
            'end_recurrence_date': end_recurrence_date.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        try:
            endpoint = self._build_endpoint('recurring')
            result = self.client.post(endpoint, data=recurring_data)
            
            self._log_operation('create_recurring_reservation')
            return result
            
        except Exception as e:
            self._handle_request_error(e, 'create_recurring_reservation')