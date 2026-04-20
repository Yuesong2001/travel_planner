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
