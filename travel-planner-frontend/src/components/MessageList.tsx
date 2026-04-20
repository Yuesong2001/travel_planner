import { User, Sparkles, Loader2 } from "lucide-react";
import type { Message } from "../types";

interface MessageListProps {
  messages: Message[];
  streamingMessage?: string;
  currentNode?: string;
  isPlanMode?: boolean;
  onSuggestedTripClick?: (prompt: string) => void;
}

// Suggested trips data (exported for use in ChatInterface)
export const SUGGESTED_TRIPS = [
  {
    id: 1,
    title: "Tokyo Cherry Blossoms",
    subtitle: "Japan · 7 Days",
    prompt:
      "Plan a 7-day trip to Tokyo, Japan from April 1-7, 2026, focusing on cherry blossoms and traditional culture from Boston",
    image:
      "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&q=80&w=800",
  },
  {
    id: 2,
    title: "Paris Romance",
    subtitle: "France · 5 Days",
    prompt:
      "Plan a 5-day romantic trip to Paris, France from June 15-19, 2025 for a couple from New York City",
    image:
      "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&q=80&w=800",
  },
  {
    id: 3,
    title: "Iceland Adventure",
    subtitle: "Iceland · 6 Days",
    prompt:
      "Plan a 6-day adventure trip to Iceland from Dec 10-15, 2025, interested in Northern Lights and nature with budget of 5000 USD from Miami",
    image:
      "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&q=80&w=800",
  },
  {
    id: 4,
    title: "Bali Relaxation",
    subtitle: "Indonesia · 10 Days",
    prompt:
      "Plan a 10-day relaxing beach vacation in Bali, Indonesia from December 20-29, 2025 for a family of 4 from Thailand",
    image:
      "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&q=80&w=800",
  },
];

const Avatar = ({ isAi, isTyping }: { isAi: boolean; isTyping?: boolean }) => (
  <div
    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-all duration-500 ${
      isAi
        ? "bg-gradient-to-br from-teal-400 to-emerald-600 text-white shadow-lg shadow-emerald-200"
        : "bg-white text-gray-800 shadow-sm border border-gray-100"
    }`}
  >
    {isAi ? (
      isTyping ? (
        <Loader2 size={18} className="animate-spin" />
      ) : (
        <Sparkles size={18} />
      )
    ) : (
      <User size={18} />
    )}
  </div>
);

const TypingIndicator = ({ action }: { action?: string }) => (
  <div className="flex items-center gap-3 text-xs text-teal-600 font-medium animate-pulse ml-1">
    <Sparkles size={12} />
    <span>{action || "Thinking..."}</span>
  </div>
);

// Map node names to user-friendly action descriptions
const getNodeAction = (nodeName?: string): string => {
  if (!nodeName) return "Thinking...";

  const actionMap: Record<string, string> = {
    determine_intent: "Understanding your request...",
    chat: "Crafting response...",
    create_plan: "Designing your itinerary...",
    synthesize_plan: "Building travel plan...",
    validate_plan: "Validating details...",
    coordinator: "Coordinating next steps...",
    judge: "Reviewing plan quality...",
  };

  return actionMap[nodeName] || `Processing (${nodeName})...`;
};

export function MessageList({
  messages,
  streamingMessage,
  currentNode,
  isPlanMode,
}: MessageListProps) {
  const getCurrentTime = () => {
    return new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 scrollbar-hide">
      <div className="max-w-3xl mx-auto pb-4">
        {/* Empty state */}
        {messages.length === 0 && !streamingMessage && (
          <div className="text-center mb-10">
            <span className="bg-white/50 backdrop-blur-md px-4 py-1.5 rounded-full text-[11px] font-medium text-gray-500 border border-white/60 shadow-sm uppercase tracking-wider">
              Today,{" "}
              {new Date().toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
              })}
            </span>
            <div className="mt-8">
              <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-teal-50 to-emerald-50 rounded-full flex items-center justify-center">
                <Sparkles size={32} className="text-teal-500" />
              </div>
              <p className="text-lg font-medium text-gray-700 mb-2">
                Ready to plan your next adventure?
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
                Tell me where you want to go, and I'll create the perfect
                itinerary for you.
              </p>
            </div>
          </div>
        )}

        {/* Date divider for first message */}
        {messages.length > 0 && (
          <div className="text-center mb-10">
            <span className="bg-white/50 backdrop-blur-md px-4 py-1.5 rounded-full text-[11px] font-medium text-gray-500 border border-white/60 shadow-sm uppercase tracking-wider">
              Today,{" "}
              {new Date().toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
              })}
            </span>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, idx) => {
          const isAi = msg.role === "ai" || msg.role === "assistant";
          const isUser = msg.role === "human" || msg.role === "user";

          return (
            <div
              key={idx}
              className={`flex gap-4 mb-6 ${
                isUser ? "flex-row-reverse" : ""
              } animate-in fade-in slide-in-from-bottom-2 duration-500`}
            >
              <Avatar isAi={isAi} />
              <div
                className={`flex flex-col max-w-[85%] md:max-w-[70%] ${
                  isUser ? "items-end" : "items-start"
                }`}
              >
                <div className="flex items-center gap-2 mb-1 opacity-70">
                  <span className="text-xs text-gray-500 font-medium">
                    {isAi ? "Travel AI" : "You"}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {getCurrentTime()}
                  </span>
                </div>

                <div
                  className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-sm transition-all hover:shadow-md ${
                    isAi
                      ? "bg-white text-gray-700 rounded-tl-none border border-gray-100"
                      : "bg-teal-600 text-white rounded-tr-none shadow-teal-200"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">
                    {msg.content}
                  </p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Streaming message */}
        {streamingMessage && (
          <div className="flex gap-4 mb-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Avatar isAi={true} isTyping={true} />
            <div className="flex flex-col max-w-[85%] md:max-w-[70%] items-start">
              <div className="flex items-center gap-2 mb-1 opacity-70">
                <span className="text-xs text-gray-500 font-medium">
                  Travel AI
                </span>
                <span className="text-[10px] text-gray-400">
                  {getCurrentTime()}
                </span>
              </div>

              <div className="bg-white px-5 py-4 rounded-2xl rounded-tl-none border border-gray-100 shadow-sm">
                {streamingMessage.trim().length === 0 ? (
                  <TypingIndicator
                    action={
                      isPlanMode ? getNodeAction(currentNode) : "Thinking..."
                    }
                  />
                ) : (
                  <p className="whitespace-pre-wrap break-words text-gray-700 text-sm leading-relaxed">
                    {streamingMessage}
                    <span className="inline-block w-1.5 h-4 bg-teal-500 animate-pulse ml-1"></span>
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
