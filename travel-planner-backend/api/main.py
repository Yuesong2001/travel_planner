"""
FastAPI Server with Server-Sent Events (SSE) for Travel Planner
Provides streaming updates for real-time frontend interaction.
"""
import os
import sys
import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path to import travel_planner
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from travel_planner.core.state import TravelState, PlanConstraints
from travel_planner.graph_builder import build_travel_graph
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Enable LangChain verbose logging
os.environ["LANGCHAIN_VERBOSE"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # Disable LangSmith if not needed

# Set up logging for LLM calls
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMLoggingHandler(BaseCallbackHandler):
    """Callback handler to log LLM inputs and outputs."""
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Log when LLM starts - only log that it started, not the prompt."""
        logger.info("=" * 100)
        logger.info("🤖🤖🤖 LLM CALL STARTED 🤖🤖🤖")
        logger.info("=" * 100)
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Log LLM responses with clear formatting."""
        logger.info("=" * 100)
        logger.info("✅✅✅ LLM RESPONSE ✅✅✅")
        logger.info("=" * 100)
        for i, generation in enumerate(response.generations):
            for j, gen in enumerate(generation):
                logger.info(f"\n📤📤📤 LLM RESPONSE {i+1}-{j+1} 📤📤📤\n")
                logger.info(gen.text)
                logger.info(f"\n{'─' * 100}\n")
        logger.info("=" * 100 + "\n")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Log LLM errors."""
        logger.error("=" * 100)
        logger.error("❌❌❌ LLM ERROR ❌❌❌")
        logger.error(f"{error}")
        logger.error("=" * 100)


# Initialize FastAPI app
app = FastAPI(
    title="Travel Planner API",
    description="Streaming API for AI-powered travel planning",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
SESSION_STATES: Dict[str, TravelState] = {}

# Initialize LLM with logging callbacks
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.0,
    callbacks=[LLMLoggingHandler()]  # Add logging callback
)
graph = None  # Will be initialized on first request


def get_graph():
    """Lazy initialization of graph to avoid startup issues."""
    global graph
    if graph is None:
        logger.info("🔧 Initializing travel planning graph...")
        graph = build_travel_graph(llm, verbose=True)
        logger.info("✅ Graph initialized successfully")
    return graph


# === Request/Response Models ===

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    messages: list
    plan: Optional[Dict[str, Any]] = None
    status: str


# === Helper Functions ===

def simplify_messages(messages: list) -> list:
    """
    Simplify LangChain messages to JSON-serializable format.
    """
    simplified = []
    for msg in messages:
        role = getattr(msg, "type", "assistant")
        content = getattr(msg, "content", "")
        simplified.append({
            "role": role,
            "content": content
        })
    return simplified


def serialize_state_for_sse(state: TravelState, print_user_request: bool = False) -> Dict[str, Any]:
    """
    Serialize state for SSE transmission.
    
    Args:
        state: The travel state to serialize
        print_user_request: Whether to print user_request in debug logs (only print once or for specific nodes)
    """
    messages = state.get("messages", [])
    plan = state.get("plan", None)
    user_request = state.get("user_request", None)
    constraints = state.get("constraints", None)

    # Get subtask progress information
    sub_tasks = state.get("sub_tasks", [])
    current_sub_task_index = state.get("current_sub_task_index", 0)
    completed_tasks_results = state.get("completed_tasks_results", {})

    result = {
        "messages": simplify_messages(messages) if messages else [],
        "plan": plan,
        "ai_response": state.get("ai_response", ""),
        "status": state.get("status", "processing"),
        "validation_errors": state.get("validation_errors", []),
        "user_request": user_request,
        "constraints": constraints,
        "sub_tasks": sub_tasks,
        "current_sub_task_index": current_sub_task_index,
        "completed_tasks_count": len(completed_tasks_results),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Debug logging
    if plan:
        print(f"📤 SSE: Sending plan with keys: {list(plan.keys())}")
    # Only print user_request when explicitly requested (to avoid duplicate logs)
    if user_request and print_user_request:
        print(f"📤 SSE: Sending user_request: {user_request}")
    if sub_tasks:
        print(f"📤 SSE: Sending subtask progress: {current_sub_task_index}/{len(sub_tasks)}")

    return result


# === API Endpoints ===

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Travel Planner API",
        "version": "1.0.0"
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint (simpler, for testing).
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Get or create session state
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = TravelState(
            user_message=request.message,
            messages=[],
            intent="chat"
        )
    else:
        state = SESSION_STATES[session_id]
        state["user_message"] = request.message

    # Run graph
    graph_app = get_graph()
    final_state = None

    for event in graph_app.stream(SESSION_STATES[session_id], {"recursion_limit": 100}):
        # Update state with each event
        for node_name, node_output in event.items():
            SESSION_STATES[session_id].update(node_output)
            final_state = SESSION_STATES[session_id]

    # Serialize response
    if final_state:
        return ChatResponse(
            session_id=session_id,
            messages=simplify_messages(final_state.get("messages", [])),
            plan=final_state.get("plan"),
            status=final_state.get("status", "completed")
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to process request")


@app.get("/chat/stream")
async def chat_stream(
    session_id: str = Query(default=None),
    message: str = Query(...)
):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Usage:
        GET /chat/stream?session_id=abc123&message=Plan%20a%20trip%20to%20Tokyo

    Returns:
        Stream of SSE events with format:
        data: {"messages": [...], "plan": {...}, "status": "..."}
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    async def event_stream():
        """Generator for SSE events."""
        try:
            # Get or create session state
            if session_id not in SESSION_STATES:
                SESSION_STATES[session_id] = TravelState(
                    user_message=message,
                    messages=[],
                    intent="chat"
                )
            else:
                state = SESSION_STATES[session_id]
                state["user_message"] = message

            # Send initial event
            yield f"data: {json.dumps({'status': 'starting', 'session_id': session_id})}\n\n"

            # Run graph and stream events
            graph_app = get_graph()

            # Track if we've printed user_request already
            user_request_printed = False
            
            for event in graph_app.stream(SESSION_STATES[session_id], {"recursion_limit": 100}):
                # Update state with each node output
                for node_name, node_output in event.items():
                    SESSION_STATES[session_id].update(node_output)

                    # Only print user_request for specific nodes or first time
                    should_print_user_request = (
                        not user_request_printed and 
                        node_name in ["chat", "normalize_input", "task_decomposer"]
                    )
                    if should_print_user_request:
                        user_request_printed = True

                    # Serialize and send current state
                    state_data = serialize_state_for_sse(SESSION_STATES[session_id], print_user_request=should_print_user_request)
                    state_data["node"] = node_name  # Include which node just ran

                    # Debug: Log which node is being sent
                    if node_name in ["synthesize_plan", "validate_plan"]:
                        print(f"🔍 SSE: Sending event for node '{node_name}'")
                        print(f"   Has plan: {state_data.get('plan') is not None}")

                    try:
                        yield f"data: {json.dumps(state_data)}\n\n"
                    except TypeError as e:
                        print(f"❌ JSON serialization error for node '{node_name}': {e}")
                        # Send error event
                        yield f"data: {json.dumps({'status': 'error', 'error': f'Serialization error: {str(e)}', 'node': node_name})}\n\n"

            # Send completion event
            final_data = serialize_state_for_sse(SESSION_STATES[session_id], print_user_request=False)
            final_data["status"] = "completed"
            print(f"🏁 SSE: Sending final completion event. Has plan: {final_data.get('plan') is not None}")
            yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            error_data = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/chat/stream")
async def chat_stream_post(request: ChatRequest):
    """
    Streaming chat endpoint using POST and SSE.
    Easier to use with more complex payloads.
    """
    import asyncio
    import threading

    session_id = request.session_id or str(uuid.uuid4())

    async def event_stream():
        """Generator for SSE events."""
        try:
            # Get or create session state
            if session_id not in SESSION_STATES:
                SESSION_STATES[session_id] = TravelState(
                    user_message=request.message,
                    messages=[],
                    intent="chat"
                )
            else:
                state = SESSION_STATES[session_id]
                state["user_message"] = request.message

            # Send initial event
            yield f"data: {json.dumps({'status': 'starting', 'session_id': session_id})}\n\n"

            # Queue to store streaming chunks and node events
            import queue
            chunk_queue = queue.Queue()
            chat_chunk_queue = queue.Queue()
            node_event_queue = queue.Queue()  # New: queue for node events
            plan_text_buffer = ""
            chat_text_buffer = ""

            def stream_plan_chunk(chunk: str):
                """Callback to stream plan chunks as they're generated."""
                chunk_queue.put(chunk)

            def stream_chat_chunk(chunk: str):
                """Callback to stream chat response chunks as they're generated."""
                print(f"📨 SSE: Got chat chunk: '{chunk[:30]}...'")
                chat_chunk_queue.put(chunk)

            # Add streaming support to state
            SESSION_STATES[session_id]["_streaming_enabled"] = True
            SESSION_STATES[session_id]["_stream_callback"] = stream_plan_chunk
            SESSION_STATES[session_id]["_chat_stream_callback"] = stream_chat_chunk
            SESSION_STATES[session_id]["_chunk_queue"] = chunk_queue
            SESSION_STATES[session_id]["_chat_chunk_queue"] = chat_chunk_queue

            print(f"✅ SSE: Streaming callbacks initialized for session {session_id}")
            print(f"🔍 SSE: State has _chat_stream_callback: {SESSION_STATES[session_id].get('_chat_stream_callback') is not None}")

            # Run graph in a background thread
            graph_app = get_graph()
            graph_done = threading.Event()
            graph_error = None

            def run_graph():
                nonlocal graph_error
                try:
                    print(f"🚀 Graph thread: Starting graph stream...")
                    for event in graph_app.stream(SESSION_STATES[session_id], {"recursion_limit": 100}):
                        for node_name, node_output in event.items():
                            print(f"📦 Graph thread: Got event from node '{node_name}'")
                            SESSION_STATES[session_id].update(node_output)
                            # Send node event to queue
                            node_event_queue.put((node_name, node_output))
                    print(f"✅ Graph thread: Completed successfully")
                except Exception as e:
                    print(f"❌ Graph thread error: {e}")
                    graph_error = e
                finally:
                    graph_done.set()

            graph_thread = threading.Thread(target=run_graph)
            graph_thread.start()

            # Stream events while graph is running
            last_node = None
            user_request_printed = False  # Track if we've printed user_request already
            
            while not graph_done.is_set() or not chat_chunk_queue.empty() or not chunk_queue.empty() or not node_event_queue.empty():
                # Check for errors
                if graph_error:
                    raise graph_error

                sent_something = False

                # Check node events (highest priority)
                while not node_event_queue.empty():
                    try:
                        node_name, node_output = node_event_queue.get_nowait()
                        
                        # Only print user_request for specific nodes or first time
                        should_print_user_request = (
                            not user_request_printed and 
                            node_name in ["chat", "normalize_input", "task_decomposer"]
                        )
                        if should_print_user_request:
                            user_request_printed = True
                        
                        # Serialize and send current state
                        state_data = serialize_state_for_sse(SESSION_STATES[session_id], print_user_request=should_print_user_request)
                        state_data["node"] = node_name

                        print(f"📤 SSE: Sending event for node '{node_name}'")
                        yield f"data: {json.dumps(state_data)}\n\n"
                        sent_something = True
                        last_node = node_name
                    except queue.Empty:
                        break
                    except TypeError as e:
                        print(f"❌ JSON serialization error for node '{node_name}': {e}")
                        # Send error event
                        yield f"data: {json.dumps({'status': 'error', 'error': f'Serialization error: {str(e)}', 'node': node_name})}\n\n"

                # Check plan chunks
                while not chunk_queue.empty():
                    try:
                        chunk = chunk_queue.get_nowait()
                        plan_text_buffer += chunk
                        chunk_data = {
                            "node": "synthesize_plan",
                            "status": "streaming",
                            "plan_chunk": chunk,
                            "plan_text": plan_text_buffer,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        sent_something = True
                    except queue.Empty:
                        break

                # Check chat chunks
                while not chat_chunk_queue.empty():
                    try:
                        chunk = chat_chunk_queue.get_nowait()
                        chat_text_buffer += chunk
                        chunk_data = {
                            "node": "chat",
                            "status": "streaming",
                            "chat_chunk": chunk,
                            "chat_text": chat_text_buffer,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                        print(f"📤 SSE: Sending chat chunk (buffer size: {len(chat_text_buffer)})")
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        sent_something = True
                    except queue.Empty:
                        break

                # If nothing was sent, wait a bit
                if not sent_something:
                    await asyncio.sleep(0.01)

            # Wait for graph to complete
            graph_thread.join(timeout=60)

            # Send final completion event
            final_data = serialize_state_for_sse(SESSION_STATES[session_id], print_user_request=False)
            final_data["status"] = "completed"
            final_data["chat_complete"] = True
            print(f"🏁 SSE: Sending final completion event. Has plan: {final_data.get('plan') is not None}")
            yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            error_data = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """
    Delete a session and its state.
    """
    if session_id in SESSION_STATES:
        del SESSION_STATES[session_id]
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """
    Retrieve current session state.
    """
    if session_id in SESSION_STATES:
        state = SESSION_STATES[session_id]
        return {
            "session_id": session_id,
            "messages": simplify_messages(state.get("messages", [])),
            "plan": state.get("plan"),
            "status": state.get("status", "active"),
            "validation_errors": state.get("validation_errors", [])
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")


if __name__ == "__main__":
    import uvicorn

    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
