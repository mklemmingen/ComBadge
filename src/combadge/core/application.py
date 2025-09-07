"""ComBadge Application Core

Main application entry point and orchestration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Fix CustomTkinter scaling tracker bug with Python 3.13
import customtkinter as ctk
# Temporarily disable scaling tracker patch to focus on reasoning display issue

from .config_manager import ConfigManager
from .error_handler import ErrorHandler
from .logging_manager import LoggingManager
from ..ui.main_window import MainWindow
from ..ui.setup_wizard import check_and_run_setup
from ..ui.components.approval_workflow import ApprovalWorkflow, ApprovalAction, ApprovalDecision, AIInterpretation
from ..intelligence.llm_manager import OllamaServerManager
from ..intelligence.reasoning_engine import ChainOfThoughtEngine
from ..intelligence.intent_classifier import IntentClassifier
from ..intelligence.entity_extractor import EntityExtractor
from ..intelligence.ai_template_selector import AITemplateSelector
from ..processors.templates.template_manager import TemplateManager
from ..processors.templates.json_generator import JSONGenerator
from ..api.client import HTTPClient
from ..api.request_builder import RequestBuilder
from ..api.response_handler import ResponseHandler


class ComBadgeApp:
    """Main application controller for ComBadge."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ComBadge application.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.error_handler = ErrorHandler()
        self.config_manager = ConfigManager(config_path)
        self.logger = LoggingManager.get_logger(__name__)
        
        self.main_window = None
        self.is_running = False
        self.ollama_manager = None
        self.reasoning_engine = None
        self.intent_classifier = None
        self.entity_extractor = None
        self.template_manager = None
        self.json_generator = None
        self.ai_template_selector = None
        self.http_client = None
        self.request_builder = None
        self.response_handler = None
        self.current_approval_workflow = None
        self.current_api_request = None
        self.current_ai_interpretation = None
        self.setup_complete = False
        
    def run(self):
        """Main application entry point."""
        try:
            self.logger.info("Starting ComBadge application")
            self._initialize_components()
            self._start_main_loop()
        except Exception as e:
            self.error_handler.handle_critical_error(e)
            sys.exit(1)
    
    def _initialize_components(self):
        """Initialize all application components."""
        # Loading configuration
        self.config = self.config_manager.load_config()
        self.logger.info("Configuration loaded successfully")
        
        # Create main window
        self.main_window = MainWindow()
        self.main_window.withdraw()  # Hide until setup is complete
        
        # Wait for window to fully initialize
        self.main_window.update_idletasks()
        
        # Temporarily bypass setup wizard due to threading issues
        self.logger.info("Bypassing setup wizard (temporary fix for threading issues)")
        
        # Proceed directly to initialize components  
        self.setup_complete = True
        self._initialize_processing_pipeline()
        self._initialize_ollama()
        
        # Ensure reasoning display is available before showing window
        if self.main_window.reasoning_display:
            self.logger.info("Reasoning display successfully initialized")
        else:
            self.logger.error("Reasoning display failed to initialize")
            
        self.main_window.deiconify()  # Show main window
        
        # Set window protocol after showing
        self.main_window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Setting up UI callbacks
        self._setup_ui_callbacks()
        
    def _initialize_processing_pipeline(self):
        """Initialize the NLP processing pipeline components."""
        try:
            self.logger.info("Initializing NLP processing pipeline...")
            
            # Initialize template manager
            self.template_manager = TemplateManager()
            self.logger.info("Template manager initialized")
            
            # Initialize template library display in UI
            self.main_window.initialize_template_library(self.template_manager)
            
            # Initialize intent classifier
            self.intent_classifier = IntentClassifier()
            self.logger.info("Intent classifier initialized")
            
            # Initialize entity extractor
            self.entity_extractor = EntityExtractor()
            self.logger.info("Entity extractor initialized")
            
            # Initialize JSON generator
            self.json_generator = JSONGenerator(self.template_manager)
            self.logger.info("JSON generator initialized")
            
            self.logger.info("NLP processing pipeline ready")
            
            # Initialize API client components
            self.http_client = HTTPClient(base_url=self.config.api.base_url)
            self.request_builder = RequestBuilder()
            self.response_handler = ResponseHandler()
            self.logger.info("API client components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize processing pipeline: {e}")
            self.error_handler.handle_error(e, "Processing pipeline initialization failed")
        
    def _initialize_ollama(self):
        """Initialize Ollama server manager."""
        try:
            self.logger.info("Initializing Ollama server manager...")
            self.ollama_manager = OllamaServerManager(
                model_name=self.config.llm.model
            )
            
            # Set up download progress callback
            self.ollama_manager.on_download_progress = self._on_model_download_progress
            
            # Initialize reasoning engine
            self.logger.info("Initializing reasoning engine...")
            self.reasoning_engine = ChainOfThoughtEngine(
                ollama_manager=self.ollama_manager
            )
            
            # Start server if not already running
            if not self.ollama_manager.is_server_running():
                self.logger.info("Starting Ollama server...")
                if self.ollama_manager.start_server():
                    self.logger.info("Ollama server started successfully")
                else:
                    self.logger.error("Failed to start Ollama server")
            
            # Initialize AI template selector
            self.ai_template_selector = AITemplateSelector(
                template_manager=self.template_manager,
                ollama_manager=self.ollama_manager
            )
            self.logger.info("AI template selector initialized")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama: {e}")
            self.error_handler.handle_error(e, "Ollama initialization failed")
        
    def _setup_ui_callbacks(self):
        """Setup UI event callbacks."""
        self.main_window.set_callbacks(
            on_submit=self._handle_text_submission,
            on_clear=self._handle_clear_request,
            on_regenerate=self._handle_regenerate_request
        )
        
        # Set up approval workflow callbacks
        self.main_window.on_approve = self._handle_approve_action
        self.main_window.on_edit = self._handle_edit_action
        self.main_window.on_reject = self._handle_reject_action
        
    def _handle_text_submission(self, text: str):
        """Handle text submission from UI.
        
        Args:
            text: Submitted text content
        """
        self.logger.info(f"Processing submitted text: {text[:50]}...")
        
        # Update UI to show processing
        self.main_window.update_status("Processing natural language input...", "processing")
        self.main_window.clear_reasoning()
        
        # Start reasoning steps
        self.main_window.add_reasoning_step(
            "Input Analysis", 
            f"Analyzing input text:\n\n{text}\n\nLength: {len(text)} characters\nType: {'Email' if '@' in text else 'Command'}"
        )
        
        # Process with structured NLP pipeline
        self._process_with_structured_pipeline(text)
        
    def _process_with_structured_pipeline(self, text: str):
        """Process user input with structured NLP pipeline: Intent → Entities → Template → JSON.
        
        Args:
            text: Input text to process
        """
        import threading
        import time
        
        def processing_thread():
            try:
                self.logger.info(f"Starting structured NLP processing for: {text[:50]}...")
                
                # Step 1: Intent Classification
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Classifying intent...", "processing")
                )
                self.main_window.add_reasoning_step(
                    "Step 1: Intent Classification",
                    "Analyzing the request to identify what operation is being requested..."
                )
                
                time.sleep(1)  # Simulate processing time
                classification_result = self.intent_classifier.classify(text)
                
                self.main_window.add_reasoning_step(
                    "Intent Classification Results",
                    f"Primary Intent: {classification_result.primary_intent.intent.value}\n" +
                    f"Confidence: {classification_result.primary_intent.confidence:.2f}\n" +
                    f"Keywords Found: {', '.join(classification_result.primary_intent.keywords_matched)}\n" +
                    f"Evidence: {', '.join(classification_result.primary_intent.evidence)}"
                )
                
                # Step 2: Entity Extraction
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Extracting entities...", "processing")
                )
                self.main_window.add_reasoning_step(
                    "Step 2: Entity Extraction",
                    "Identifying specific details like vehicle IDs, dates, locations, people..."
                )
                
                time.sleep(1)  # Simulate processing time
                entities = self.entity_extractor.extract(text)
                
                entity_details = []
                for entity_type, entity_list in entities.entity_groups.items():
                    if entity_list:
                        values = [entity.value for entity in entity_list]
                        avg_confidence = sum(entity.confidence for entity in entity_list) / len(entity_list)
                        entity_details.append(f"• {entity_type.value}: {', '.join(values)} (confidence: {avg_confidence:.2f})")
                        
                if entity_details:
                    self.main_window.add_reasoning_step(
                        "Entity Extraction Results",
                        "\n".join(entity_details)
                    )
                else:
                    self.main_window.add_reasoning_step(
                        "Entity Extraction Results",
                        "No specific entities were identified in this request."
                    )
                
                # Step 3: AI Template Selection
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("AI selecting best template...", "processing")
                )
                self.main_window.add_reasoning_step(
                    "Step 3: AI Template Selection",
                    "Using AI to analyze input and select the most appropriate template based on examples and metadata..."
                )
                
                time.sleep(1)  # Simulate processing time
                
                # Use AI to select template
                template_choice = self.ai_template_selector.select_template(text)
                template_path = template_choice.template_name
                
                # Display AI selection reasoning
                confidence_text = f"{template_choice.confidence:.0%} ({template_choice.confidence_level.value})"
                reasoning_text = f"Selected template: {template_path}\n" + \
                               f"Confidence: {confidence_text}\n" + \
                               f"AI Reasoning: {template_choice.reasoning}"
                
                if template_choice.key_factors:
                    reasoning_text += f"\nKey factors: {', '.join(template_choice.key_factors)}"
                
                if template_choice.alternative_templates:
                    reasoning_text += f"\nAlternatives considered: {', '.join(template_choice.alternative_templates)}"
                
                self.main_window.add_reasoning_step(
                    "AI Template Selection Results",
                    reasoning_text
                )
                
                # Get the selected template
                template = self.template_manager.get_template(template_path)
                if template:
                    template_metadata = template.get('template_metadata', {})
                    self.main_window.add_reasoning_step(
                        "Template Details",
                        f"API Endpoint: {template_metadata.get('api_endpoint', 'N/A')}\n" +
                        f"HTTP Method: {template_metadata.get('http_method', 'POST')}\n" +
                        f"Required entities: {', '.join(template_metadata.get('required_entities', []))}"
                    )
                else:
                    self.main_window.add_reasoning_step(
                        "Template Selection Warning",
                        f"Warning: Template '{template_path}' not found. Using fallback structure."
                    )
                
                # Step 4: JSON Generation
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Generating API request...", "processing")
                )
                self.main_window.add_reasoning_step(
                    "Step 4: JSON Generation",
                    "Populating the selected template with extracted entity data..."
                )
                
                time.sleep(1)  # Simulate processing time
                
                # Generate JSON request
                if template:
                    # Convert entity groups to simple dict format for JSON generator
                    entity_dict = {k.value: [e.value for e in v] for k, v in entities.entity_groups.items()}
                    api_request = self.json_generator.generate_request(
                        template_path,
                        entity_dict,
                        {"source": "user_input", "original_text": text}
                    )
                else:
                    # Fallback - create basic request structure
                    api_request = {
                        "method": "POST",
                        "endpoint": "/api/unknown",
                        "data": {
                            "intent": classification_result.primary_intent.intent.value,
                            "confidence": classification_result.primary_intent.confidence,
                            "original_request": text,
                            "entities": {k.value: [e.value for e in v] for k, v in entities.entity_groups.items()}
                        }
                    }
                
                self.main_window.add_reasoning_step(
                    "JSON Generation Complete",
                    f"Successfully generated API request with {len(api_request.get('data', {}))} fields"
                )
                
                # Display API Results and Approval Workflow
                def show_approval_workflow():
                    if self.main_window:
                        self.main_window.update_status("Processing complete - Review and approve request", "success")
                        self.main_window.show_api_results(api_request)
                        
                        # Mark reasoning as complete
                        if self.main_window.reasoning_display:
                            self.main_window.reasoning_display.complete_reasoning()
                        
                        # Create AI interpretation summary
                        ai_interpretation = AIInterpretation(
                            original_text=text,
                            intent=classification_result.primary_intent.intent.value,
                            intent_confidence=classification_result.primary_intent.confidence,
                            entities={k.value: [e.value for e in v] for k, v in entities.entity_groups.items()},
                            summary=f"Request to {classification_result.primary_intent.intent.value.replace('_', ' ').lower()}",
                            proposed_action=f"Execute {classification_result.primary_intent.intent.value} operation",
                            generated_request=api_request,
                            overall_confidence=(classification_result.primary_intent.confidence + 
                                              (sum(sum(e.confidence for e in entity_list) / len(entity_list) 
                                                  for entity_list in entities.entity_groups.values() if entity_list) / max(1, len(entities.entity_groups))
                                               if entities.entity_groups else classification_result.primary_intent.confidence)
                                              ) / 2
                        )
                        
                        # Store current request for approval buttons
                        self.current_api_request = api_request
                        self.current_ai_interpretation = ai_interpretation
                
                self.main_window.after_idle(show_approval_workflow)
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error in structured processing pipeline: {error_msg}")
                self.main_window.after_idle(
                    lambda: self.main_window.update_status(f"Processing failed: {error_msg}", "error")
                )
                
        # Start processing in background thread
        thread = threading.Thread(target=processing_thread, daemon=True)
        thread.start()
        
    def _show_approval_workflow(self, api_request: Dict[str, Any], ai_interpretation: AIInterpretation):
        """Show the approval workflow for the generated API request.
        
        Args:
            api_request: Generated API request
            ai_interpretation: AI's interpretation of the request
        """
        # Create approval workflow dialog
        import customtkinter as ctk
        
        approval_window = ctk.CTkToplevel(self.main_window)
        approval_window.title("Request Approval")
        approval_window.geometry("900x700")
        approval_window.transient(self.main_window)
        approval_window.grab_set()
        
        self.current_approval_workflow = ApprovalWorkflow(
            approval_window,
            on_approve=self._handle_approval_decision,
            on_reject=self._handle_approval_decision,
            on_regenerate=self._handle_regenerate_feedback,
            user_id="user"
        )
        
        # Load the interpretation for review
        self.current_approval_workflow.load_interpretation(ai_interpretation)
        
        # Pack the workflow
        self.current_approval_workflow.pack(fill="both", expand=True, padx=10, pady=10)
        
    def _handle_approval_decision(self, decision: ApprovalDecision):
        """Handle approval workflow decision.
        
        Args:
            decision: User's approval decision
        """
        self.logger.info(f"Approval decision: {decision.action.value}")
        
        if decision.action == ApprovalAction.APPROVE:
            self._execute_api_request(decision.original_request, decision)
            
        elif decision.action == ApprovalAction.EDIT_APPROVE:
            # Use modified request if available
            request_to_send = decision.modified_request or decision.original_request
            self._execute_api_request(request_to_send, decision)
            
        elif decision.action == ApprovalAction.REGENERATE:
            # Re-run pipeline with feedback
            if decision.feedback:
                enhanced_input = f"{decision.original_request.get('original_text', '')} {decision.feedback}"
                self._handle_text_submission(enhanced_input)
            else:
                self.main_window.update_status("Please provide feedback for regeneration", "warning")
                
        elif decision.action == ApprovalAction.REJECT:
            self.main_window.update_status("Request rejected", "idle")
            self.logger.info(f"Request rejected with feedback: {decision.feedback}")
            
        # Close approval workflow
        if self.current_approval_workflow:
            self.current_approval_workflow.close()
            self.current_approval_workflow = None
    
    def _execute_api_request(self, api_request: Dict[str, Any], decision: ApprovalDecision):
        """Execute the approved API request.
        
        Args:
            api_request: API request to execute
            decision: Approval decision details
        """
        import threading
        
        def execute_request():
            try:
                self.main_window.after_idle(
                    lambda: self.main_window.update_status("Sending API request...", "processing")
                )
                
                # Build HTTP request
                http_request = self.request_builder.build_request(
                    method=api_request.get('method', 'POST'),
                    endpoint=api_request.get('endpoint', '/api/unknown'),
                    data=api_request.get('data', {})
                )
                
                # Execute request
                response = self.http_client.execute_request(http_request)
                
                # Handle response
                result = self.response_handler.handle_response(response)
                
                # Show result in UI
                self.main_window.after_idle(
                    lambda: self._show_api_response(result, api_request, decision)
                )
                
            except Exception as e:
                self.logger.error(f"API request failed: {e}")
                self.main_window.after_idle(
                    lambda: self.main_window.update_status(f"API request failed: {str(e)}", "error")
                )
        
        # Execute in background thread
        thread = threading.Thread(target=execute_request, daemon=True)
        thread.start()
        
    def _show_api_response(self, response_result: Dict[str, Any], 
                          original_request: Dict[str, Any], 
                          decision: ApprovalDecision):
        """Show API response in the UI.
        
        Args:
            response_result: Processed API response
            original_request: Original API request
            decision: Approval decision
        """
        if response_result.get('success'):
            self.main_window.update_status("API request successful!", "success")
            
            # Show response in API results panel
            response_display = {
                "method": original_request.get('method', 'POST'),
                "endpoint": original_request.get('endpoint'),
                "request_data": original_request.get('data'),
                "response": response_result.get('data'),
                "status_code": response_result.get('status_code'),
                "timestamp": datetime.now().isoformat()
            }
            
            self.main_window.show_api_results(response_display)
            
        else:
            error_msg = response_result.get('error', 'Unknown error')
            self.main_window.update_status(f"API request failed: {error_msg}", "error")
            
        # Log the transaction
        self.logger.info(f"API transaction completed - Success: {response_result.get('success')}")
    
    def _on_model_download_progress(self, progress):
        """Handle model download progress updates.
        
        Args:
            progress: DownloadProgress object with download status
        """
        # Update UI on main thread
        def update_ui():
            if hasattr(self.main_window, 'update_status'):
                if progress.status == "success":
                    status_msg = "AI model ready! Processing..."
                    self.main_window.update_status(status_msg, "processing")
                elif progress.total > 0:
                    mb_completed = progress.completed / (1024 * 1024)
                    mb_total = progress.total / (1024 * 1024)
                    status_msg = f"Downloading AI model: {mb_completed:.0f}/{mb_total:.0f} MB ({progress.percent:.1f}%)"
                    self.main_window.update_status(status_msg, "processing")
                else:
                    status_msg = f"Downloading AI model... {progress.status}"
                    self.main_window.update_status(status_msg, "processing")
                
        self.main_window.after_idle(update_ui)
        
    def _handle_clear_request(self):
        """Handle clear request from UI."""
        self.logger.info("Clearing UI content")
        
    def _handle_regenerate_request(self):
        """Handle regenerate request from UI."""
        self.logger.info("Regenerating last result")
        
        # Get current input and reprocess
        current_text = self.main_window.get_input_text()
        if current_text.strip():
            self._handle_text_submission(current_text)
        
    def _start_main_loop(self):
        """Start the main application event loop."""
        self.is_running = True
        self.logger.info("Starting main event loop")
        self.main_window.mainloop()
        
    def _on_closing(self):
        """Handle application closing."""
        self.logger.info("Shutting down ComBadge application")
        self.is_running = False
        
        # Cleanup resources
        self._cleanup()
        
        if self.main_window:
            self.main_window.destroy()
            
    def _cleanup(self):
        """Clean up application resources."""
        # Clean up event handlers
        if self.main_window and hasattr(self.main_window, 'event_handler'):
            self.main_window.event_handler.cleanup()
    
    def _handle_approve_action(self):
        """Handle approve button click from MainWindow."""
        if not self.current_api_request or not self.current_ai_interpretation:
            self.main_window.update_status("No request to approve", "warning")
            return
        
        # Create approval decision
        decision = ApprovalDecision(
            action=ApprovalAction.APPROVE,
            timestamp=datetime.now(),
            user_id="user",
            original_request=self.current_api_request.copy()
        )
        
        self.logger.info("User approved API request directly")
        self._execute_api_request(self.current_api_request, decision)
    
    def _handle_edit_action(self):
        """Handle edit button click from MainWindow."""
        if not self.current_api_request or not self.current_ai_interpretation:
            self.main_window.update_status("No request to edit", "warning")
            return
        
        # Show the full approval workflow for editing
        self._show_approval_workflow(self.current_api_request, self.current_ai_interpretation)
    
    def _handle_reject_action(self):
        """Handle reject button click from MainWindow."""
        if not self.current_api_request or not self.current_ai_interpretation:
            self.main_window.update_status("No request to reject", "warning")
            return
        
        # Create rejection decision
        decision = ApprovalDecision(
            action=ApprovalAction.REJECT,
            timestamp=datetime.now(),
            user_id="user",
            original_request=self.current_api_request.copy(),
            feedback="Rejected from main interface"
        )
        
        self.logger.info("User rejected API request")
        self.main_window.update_status("Request rejected", "idle")
        self.main_window.clear_api_results()
        
        # Clear current request
        self.current_api_request = None
        self.current_ai_interpretation = None
    
    def _handle_regenerate_feedback(self, feedback: str):
        """Handle regenerate action with user feedback.
        
        Args:
            feedback: User feedback for regeneration
        """
        if not self.current_api_request or not self.current_ai_interpretation:
            self.main_window.update_status("No request to regenerate", "warning")
            return
        
        # Get original text and enhance with feedback
        original_text = self.current_ai_interpretation.original_text
        enhanced_input = f"{original_text} {feedback}" if feedback else original_text
        
        self.logger.info(f"Regenerating request with feedback: {feedback}")
        
        # Close approval workflow if open
        if self.current_approval_workflow:
            self.current_approval_workflow.destroy()
            self.current_approval_workflow = None
        
        # Reprocess with enhanced input
        self._handle_text_submission(enhanced_input)