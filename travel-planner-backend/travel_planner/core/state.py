from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

# ============= Pydantic Models for Plan Schema =============

class PlanConstraintsModel(BaseModel):
    """Structured constraints for travel planning."""
    origin: Optional[str] = Field(None, description="Departure location for flight search (e.g., 'San Francisco', 'LAX')")
    budget_limit: Optional[float] = Field(None, description="Maximum budget in the specified currency")
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR, etc.)")
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Trip end date (YYYY-MM-DD)")
    interests: List[str] = Field(default_factory=list, description="Traveler interests")
    travelers: Optional[int] = Field(None, description="Number of travelers")
    travel_type: Optional[str] = Field(None, description="Type of travel (e.g., honeymoon, family vacation)")

class ItineraryItem(BaseModel):
    """Single item in the daily itinerary."""
    time: str = Field(..., description="Time or time range (e.g., 'Morning', '09:00-12:00')")
    place: str = Field(..., description="Place or activity name")
    reason: str = Field(..., description="Why this place/activity fits the trip")

class DayItinerary(BaseModel):
    """Itinerary for a single day."""
    day: int = Field(..., description="Day number (1, 2, 3, ...)")
    summary: str = Field(..., description="Brief summary of the day's theme")
    items: List[ItineraryItem] = Field(..., description="List of activities for the day")

class BudgetInfo(BaseModel):
    """Budget information."""
    currency: Optional[str] = Field(None, description="Currency code")
    estimated_total: Optional[float] = Field(None, description="Total estimated cost")

class WeatherInfo(BaseModel):
    """Weather information for the destination."""
    temperature: Optional[str] = Field(None, description="Temperature range (e.g., '15-25°C')")
    condition: Optional[str] = Field(None, description="Weather condition (e.g., 'Sunny', 'Rainy')")
    description: Optional[str] = Field(None, description="Detailed weather description")

class TravelPlan(BaseModel):
    """Complete travel plan schema."""
    destination: str = Field(..., description="Destination name")
    constraints: PlanConstraintsModel = Field(..., description="Travel constraints")
    days: List[DayItinerary] = Field(..., description="Day-by-day itinerary")
    budget: BudgetInfo = Field(..., description="Budget information")
    weather: Optional[WeatherInfo] = Field(None, description="Weather information")
    generated_at: str = Field(..., description="ISO timestamp when plan was generated")
    version: int = Field(1, description="Plan version number")

# ============= TypedDict for State (for LangGraph) =============

class PlanConstraints(TypedDict, total=False):
    """Structured constraints for travel planning."""
    origin: Optional[str]  # NEW: Departure location for flight search
    budget_limit: Optional[float]
    currency: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    interests: List[str]
    travelers: Optional[int]
    travel_type: Optional[str]  # e.g., "honeymoon", "graduation trip", "family vacation", "solo adventure"

class TravelState(TypedDict, total=False):
    # User input
    user_message: str
    user_request: Dict[str, Any]  # Structured travel request (destination, duration, budget, etc.)

    # Chat and conversation (unified to messages only)
    intent: str  # "chat", "plan", or "refine"
    ai_response: str
    messages: List[BaseMessage]  # Standard message format (unified)

    # Plan refinement (for incremental modifications)
    refinement_request: Optional[Dict[str, Any]]  # Details of what to modify in existing plan

    # Task decomposition
    sub_tasks: List[str]
    current_sub_task_index: int
    current_sub_task: str

    # Tool execution
    tool_results: List[Any]
    completed_tasks_results: Dict[str, Any]  # Dictionary mapping sub-task to result

    # Planning
    next_step: str  # "judge", "synthesize", "validate", "feedback", etc.
    travel_plan: Optional[str]  # Text version (backward compatible)
    final_plan: Optional[str]
    plan: Optional[Dict[str, Any]]  # Structured plan JSON
    plan_history: List[Dict[str, Any]]  # History of plan versions
    constraints: Optional[PlanConstraints]  # Extracted constraints

    # Validation and feedback
    validation_errors: List[str]  # Errors from plan validation
    user_feedback: Optional[str]  # User feedback on the plan
    feedback_mode: bool  # Whether we're waiting for user feedback

    # Agent decision making
    judgement: Dict[str, Any]
    max_retries: int
    current_retries: int

    # Status and metadata
    status: str  # "processing", "completed", "failed", "awaiting_feedback"
    errors: List[str]  # General errors
