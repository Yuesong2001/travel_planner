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

# Pinecone (optional but recommended for RAG and plan history)
PINECONE_API_KEY=pcsk-...
PINECONE_INDEX_NAME=travel-planner   # default: travel-planner
PINECONE_CLOUD=aws                   # default: aws
PINECONE_REGION=us-east-1            # default: us-east-1

# Optional
OPENAI_MODEL=gpt-4-turbo-preview
API_PORT=8000
DEBUG=false
```

### Pinecone Setup

The backend uses Pinecone for two purposes:
1. **Knowledge base RAG** - destinations, attractions, and restaurants are indexed and recalled to augment LLM context.
2. **Plan history** - successful plans are indexed and similar past plans are retrieved as few-shot examples.

To enable Pinecone:

1. Sign up at [pinecone.io](https://pinecone.io) and create an API key.
2. Set `PINECONE_API_KEY` in your `.env` file. The index will be **auto-created** on first use (serverless, cosine metric, 1536 dimensions to match `text-embedding-3-small`).
3. (Optional) Pre-seed the knowledge base with popular cities:

```bash
cd travel-planner-backend
python -m scripts.seed_pinecone
# or with custom cities:
python -m scripts.seed_pinecone --cities "Tokyo,Paris,Bali"
```

If `PINECONE_API_KEY` is not set, all RAG calls become no-ops and the system falls back to its previous behavior.

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

# Travel Planner Frontend

Modern, beautiful React frontend for the AI-powered travel planning assistant.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Running the Development Server

```bash
npm run dev
```

The app will start on `http://localhost:5173`

Expected output:
```
VITE v7.2.4  ready in 652 ms
➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ChatInterface.tsx       # Main app container
│   │   ├── MessageList.tsx         # Chat message display
│   │   ├── InputBox.tsx            # User input with send button
│   │   └── PlanDisplay.tsx         # Travel plan visualization
│   ├── services/
│   │   └── api.ts                  # API client with SSE
│   ├── types/
│   │   └── index.ts                # TypeScript type definitions
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles (Tailwind)
├── public/                  # Static assets
├── index.html              # HTML template
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript config
├── tailwind.config.js      # Tailwind config (if exists)
└── postcss.config.js       # PostCSS config
```

## 🎨 Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS v4** - Styling
- **Server-Sent Events (SSE)** - Real-time streaming

## 🧩 Components

### ChatInterface

Main component that orchestrates the entire UI.

**Features:**
- Manages conversation state
- Handles SSE streaming
- Coordinates message display and plan updates
- Session management (new session button)
- Status indicator

**Location:** `src/components/ChatInterface.tsx`

### MessageList

Displays chat messages with beautiful styling.

**Features:**
- Scrollable message history
- Different styles for user/AI messages
- Avatar icons (👤 for user, 🤖 for AI)
- Empty state with example prompt
- Smooth animations

**Location:** `src/components/MessageList.tsx`

### InputBox

User input area with send button.

**Features:**
- Text input with airplane icon
- Gradient send button (blue to purple)
- Loading spinner during processing
- Disabled state when streaming
- Submit on Enter key

**Location:** `src/components/InputBox.tsx`

### PlanDisplay

Shows the generated travel plan.

**Features:**
- Plan title with gradient text
- Total cost display with 💰 icon
- Day-by-day itinerary cards
- Activity timeline with time badges
- Location and cost info for each activity
- Validation errors display
- Notes section
- Collapsible raw JSON viewer

**Location:** `src/components/PlanDisplay.tsx`

## 🎨 Styling

### Tailwind CSS v4

The app uses Tailwind CSS v4 with modern gradient designs:

**Color Scheme:**
- **Primary**: Blue (500-600) to Purple (600)
- **Background**: Gradient from blue-50 to purple-50
- **User messages**: Blue gradient
- **AI messages**: Gray gradient with border
- **Success states**: Emerald green
- **Warnings**: Amber/Yellow
- **Errors**: Red/Rose

**Key Design Elements:**
- Rounded corners (`rounded-xl`, `rounded-2xl`)
- Soft shadows (`shadow-lg`, `shadow-xl`)
- Gradients for visual interest
- Smooth transitions and animations
- Hover effects on interactive elements

### Customization

Edit `src/index.css` to customize global styles:

```css
@import "tailwindcss";

/* Your custom styles here */
```

## 🔌 API Integration

### API Client

Location: `src/services/api.ts`

**Methods:**

#### `streamChat(message, onEvent, onError, onComplete)`

Sends a message and receives streaming updates.

```typescript
apiClient.streamChat(
  "Plan a trip to Paris",
  (event) => {
    // Handle streaming event
    console.log(event.messages, event.plan, event.status);
  },
  (error) => {
    // Handle error
    console.error(error);
  },
  () => {
    // Handle completion
    console.log("Streaming complete");
  }
);
```

#### `resetSession()`

Clears the current session and starts fresh.

```typescript
apiClient.resetSession();
```

### Event Types

The SSE stream sends events with this structure:

```typescript
interface StreamEvent {
  messages?: Message[];
  plan?: Plan;
  status?: string;
  node?: string;
  validation_errors?: string[];
  error?: string;
}
```

## 📝 TypeScript Types

### Message

```typescript
interface Message {
  role: "human" | "ai" | "user" | "assistant" | string;
  content: string;
}
```

### Plan

```typescript
interface Plan {
  title?: string;
  estimated_total?: number;
  currency?: string;
  days?: Day[];
  notes?: string[];
}

interface Day {
  day: number;
  activities: Activity[];
}

interface Activity {
  time?: string;
  activity: string;
  location?: string;
  cost?: number;
}
```

## 🛠️ Development

### Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

### Linting

```bash
npm run lint
```

### Type Checking

```bash
npx tsc --noEmit
```

## 🎯 Features

### Real-time Streaming

- Uses Server-Sent Events (SSE) for live updates
- Shows processing status and current node
- Updates messages and plan progressively
- Displays validation errors in real-time

### Session Management

- Each conversation has a unique session ID
- "New Session" button resets conversation
- Session state managed automatically

### Responsive Design

- Works on desktop and tablet
- Two-column layout (chat | plan)
- Smooth scrolling and animations
- Adaptive spacing and sizing

### User Experience

- Empty states with helpful prompts
- Loading indicators during processing
- Visual feedback for all actions
- Smooth transitions and animations
- Clear error messaging

## 🐛 Troubleshooting

### Tailwind Styles Not Working

1. Check that `index.css` is imported in `main.tsx`
2. Verify PostCSS configuration
3. Restart dev server

```bash
# Stop server (Ctrl+C)
npm run dev
```

### API Connection Failed

1. Ensure backend is running on port 8000
2. Check CORS settings in backend
3. Verify API URL in `api.ts`:

```typescript
const API_URL = "http://localhost:8000";
```

### Build Errors

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

### TypeScript Errors

```bash
# Check types
npx tsc --noEmit

# Update types
npm install --save-dev @types/react @types/react-dom
```

## 🚀 Deployment

### Static Hosting (Vercel, Netlify, etc.)

1. Build the project:

```bash
npm run build
```

2. Deploy the `dist/` directory

3. Configure environment variables if needed

### Environment Variables

Create `.env` file if API URL changes:

```bash
VITE_API_URL=https://your-backend-url.com
```

Update `api.ts`:

```typescript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /path/to/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 📦 Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## 🎨 Customization

### Change Color Scheme

Edit component classes to use different Tailwind colors:

```tsx
// Change from blue-purple to green-teal
className="bg-gradient-to-r from-green-500 to-teal-600"
```

### Modify Layout

Edit `ChatInterface.tsx` to change the layout:

```tsx
// Change column widths
<div className="w-1/2">  // Change to w-1/3, w-2/3, etc.
```

### Add New Features

1. Create new component in `src/components/`
2. Import and use in `ChatInterface.tsx`
3. Add types to `src/types/index.ts` if needed

## 🌟 UI Highlights

### Gradient Design
- Header with gradient logo
- Gradient buttons (blue to purple)
- Gradient plan title
- Gradient backgrounds throughout

### Smooth Animations
- Fade-in animations for messages
- Button scale on click
- Spinner during loading
- Hover effects on cards

### Icons & Emojis
- ✈️ Airplane for travel theme
- 💬 Chat bubble for messages
- 📋 Clipboard for plans
- 💰 Money bag for costs
- 📍 Location pin for places
- 🤖 Robot for AI
- 👤 Person for user

## 📚 Additional Resources

- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Server-Sent Events Guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## 📄 License

Part of the Travel Planner project.
