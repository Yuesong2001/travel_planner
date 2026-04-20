# Travel Planner Backend

AI-powered travel planning backend built with LangGraph, LangChain, and FastAPI.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API Key

### Installation

1. **Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

2. **Set up environment variables**

Create a `.env` file in the project root (Travel Planner/.env):

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Running the Server

```bash
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

The server will start on `http://127.0.0.1:8000` with auto-reload enabled.

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

## 📡 API Endpoints

### Health Check

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Travel Planner API",
  "version": "1.0.0"
}
```

### Chat Stream (POST)

Send a message and receive streaming updates via Server-Sent Events (SSE).

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Plan a 3-day honeymoon to Paris with a budget of $2000"
  }'
```

**Request Body:**
```json
{
  "message": "string",
  "session_id": "string (optional)"
}
```

**Response:** SSE stream with events:
```
data: {"messages": [...], "plan": {...}, "status": "processing", "node": "chat_node"}

data: {"messages": [...], "plan": {...}, "status": "completed"}
```

### Get Session (GET)

Retrieve session data including messages and plan.

```bash
curl http://localhost:8000/session/{session_id}
```

**Response:**
```json
{
  "session_id": "uuid",
  "messages": [...],
  "plan": {...},
  "created_at": "timestamp"
}
```

### Delete Session (DELETE)

Delete a session and its data.

```bash
curl -X DELETE http://localhost:8000/session/{session_id}
```

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

## 🏗️ Architecture

```
backend/
├── api/
│   └── main.py              # FastAPI server with SSE streaming
├── travel_planner/
│   ├── core/
│   │   ├── state.py         # State definitions and schemas
│   │   └── prompt_templates.py  # LLM prompt templates
│   ├── nodes/               # LangGraph node implementations
│   │   ├── chat_node.py            # Initial chat handler
│   │   ├── coordinator.py          # Task coordination
│   │   ├── task_decomposer.py      # Break down complex tasks
│   │   ├── judgement_agent.py      # Judge sub-task results
│   │   ├── plan_agent.py           # Execute planning tasks
│   │   ├── plan_synthesizer.py     # Synthesize final plan
│   │   ├── validate_plan.py        # Validate plan constraints
│   │   └── result_collector.py     # Collect and format results
│   ├── routers/
│   │   └── main_routers.py  # Graph routing logic
│   ├── utils/
│   │   ├── constraints_utils.py    # Constraint parsing and validation
│   │   └── tools_def.py            # Tool definitions
│   └── graph_builder.py     # LangGraph workflow builder
└── requirements.txt         # Python dependencies
```

## 🧠 LangGraph Workflow

The backend uses a sophisticated LangGraph workflow:

1. **chat_node**: Initial user message processing
2. **coordinator**: Analyzes request and creates execution plan
3. **task_decomposer**: Breaks down complex tasks into sub-tasks
4. **plan_agent**: Executes individual planning tasks
5. **judgement_agent**: Reviews and validates sub-task results
6. **plan_synthesizer**: Combines results into final travel plan
7. **validate_plan**: Validates plan against constraints
8. **result_collector**: Formats and returns final response

## 🔑 Key Features

### LLM-Based Constraint Parsing

The system supports natural language constraints in both English and Chinese:

```python
# English
"Plan a 3-day trip to Tokyo with a budget of $2000"

# Chinese
"帮我规划一个3天的东京旅行，预算2000美元"
```

Constraints are automatically extracted:
- **Duration**: Number of days
- **Budget**: Total budget amount
- **Destination**: Target location
- **Trip Type**: honeymoon, business, family, etc.

### Session Management

- Each conversation is tracked by a unique session ID
- Sessions store message history and generated plans
- Sessions can be retrieved or deleted via API

### Plan Validation

Automatic validation ensures:
- Plan duration matches requested days
- Total cost stays within budget
- All required fields are present
- Logical consistency of itinerary

### Streaming Updates

Real-time streaming via SSE provides:
- Live message updates
- Progressive plan generation
- Current processing node status
- Validation error notifications

## 🛠️ Development

### Adding New Nodes

Create a new node in `travel_planner/nodes/`:

```python
from travel_planner.core.state import State

def my_new_node(state: State) -> State:
    """
    Node description and purpose.
    """
    # Node implementation
    return state
```

Register in `graph_builder.py`:

```python
graph.add_node("my_node", my_new_node)
graph.add_edge("previous_node", "my_node")
```

### Customizing Prompts

Edit prompt templates in `travel_planner/core/prompt_templates.py`:

```python
MY_PROMPT = """
Your custom prompt template here.
"""
```

### Running Tests

```bash
# Test the health endpoint
curl http://localhost:8000/

# Test chat streaming
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a trip to Tokyo"}'
```

## 🐛 Troubleshooting

### Import Errors

```bash
# Run the fix script
python fix_imports.py
```

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### OpenAI API Errors

- Check your `.env` file has valid `OPENAI_API_KEY`
- Ensure API key has sufficient credits
- Verify network connectivity to OpenAI API

### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install langchain langgraph langchain-openai
```

## 📝 Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
OPENAI_MODEL=gpt-4-turbo-preview
API_PORT=8000
DEBUG=false
```

## 🚀 Deployment

### Production Setup

1. Use a production ASGI server:

```bash
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. Set environment variables in production

3. Use a reverse proxy (nginx, Caddy)

4. Enable HTTPS

5. Set up monitoring and logging

### Docker (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "api/main.py"]
```

Build and run:

```bash
docker build -t travel-planner-backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key travel-planner-backend
```

## 📚 Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

## 📄 License

Part of the Travel Planner project.
