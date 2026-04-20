import { useState, useRef, useEffect, useMemo } from "react";
import {
  Compass,
  RotateCcw,
  MapPin,
  Calendar,
  Users,
  CheckCircle2,
  Leaf,
  Landmark,
  Utensils,
  Camera,
  Plane,
  Settings,
  X,
  Check,
} from "lucide-react";
import { MessageList, SUGGESTED_TRIPS } from "./MessageList";
import { InputBox } from "./InputBox";
import { PlanDisplay } from "./PlanDisplay";
import { apiClient } from "../services/api";
import { generateMustHaves } from "../utils/mustHavesUtils";
import type {
  Message,
  Plan,
  StreamEvent,
  UserRequest,
  Constraints,
} from "../types";

// Background options
const SOLID_COLORS = [
  { name: "Soft Gray", value: "#f3f4f6", gradient: "bg-gray-100" },
  {
    name: "Ocean Blue",
    value: "#e0f2fe",
    gradient: "bg-gradient-to-br from-blue-50 to-cyan-100",
  },
  {
    name: "Sunset Pink",
    value: "#fce7f3",
    gradient: "bg-gradient-to-br from-pink-50 to-rose-100",
  },
];

const BACKGROUND_IMAGES = [
  {
    name: "Road Trip",
    url: "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&q=80&w=2021",
  },
  {
    name: "Travel",
    url: "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&q=80&w=2021",
  },
  {
    name: "Airplane",
    url: "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&q=80&w=2021",
  },
  {
    name: "Beach",
    url: "https://images.unsplash.com/photo-1473116763249-2faaef81ccda?q=80&w=2392&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
  },
  {
    name: "Tropical",
    url: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&q=80&w=2021",
  },
  {
    name: "Mountains",
    url: "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&q=80&w=2021",
  },
];

// TEMP: Mock plan data for development - SET TO null TO DISABLE
// const MOCK_PLAN: Plan | null = {
//   destination: "Iceland",
//   constraints: {
//     origin: "Miami, USA",
//     budget_limit: 5000,
//     currency: "USD",
//     start_date: "2025-12-10",
//     end_date: "2025-12-15",
//     interests: ["Northern Lights", "nature"],
//     travelers: 1,
//     travel_type: "adventure trip",
//   },
//   days: [
//     {
//       day: 1,
//       summary: "Arrival and exploring Reykjavík",
//       items: [
//         {
//           time: "Morning",
//           place: "Reykjavík",
//           reason:
//             "Explore the vibrant capital known for its colorful buildings and cultural scene.",
//           travel_time_to_next: 13,
//         },
//         {
//           time: "Afternoon",
//           place: "Hallgrímskirkja",
//           reason: "Visit this iconic church for panoramic views of the city.",
//           travel_time_to_next: 13,
//         },
//         {
//           time: "Evening",
//           place: "Icelandic Street Food",
//           reason: "Enjoy local cuisine in a casual setting.",
//         },
//       ],
//     },
//     {
//       day: 2,
//       summary: "Golden Circle Tour and Northern Lights",
//       items: [
//         {
//           time: "Morning",
//           place: "Þingvellir National Park",
//           reason:
//             "Experience the beauty and history of this UNESCO World Heritage site.",
//           travel_time_to_next: 40,
//         },
//         {
//           time: "Afternoon",
//           place: "Geysir Geothermal Area",
//           reason: "Witness the geothermal activity and Strokkur geyser.",
//         },
//         {
//           time: "Evening",
//           place: "Northern Lights Tour",
//           reason: "Join a guided tour to see the magical Northern Lights.",
//         },
//       ],
//     },
//     {
//       day: 3,
//       summary: "Nature Exploration",
//       items: [
//         {
//           time: "Morning",
//           place: "Gullfoss Waterfall",
//           reason: "Visit one of Iceland's most famous waterfalls.",
//           travel_time_to_next: 60,
//         },
//         {
//           time: "Afternoon",
//           place: "Öxarárfoss",
//           reason: "Enjoy a scenic hike to this beautiful waterfall.",
//           travel_time_to_next: 84,
//         },
//         {
//           time: "Evening",
//           place: "Midgard Restaurant & Bar",
//           reason: "Dine at a highly-rated restaurant with local flavors.",
//         },
//       ],
//     },
//     {
//       day: 4,
//       summary: "Glacier Lagoon and Nature Activities",
//       items: [
//         {
//           time: "Morning",
//           place: "Jökulsárlón Glacier Lagoon",
//           reason: "Explore the stunning lagoon filled with icebergs.",
//         },
//         {
//           time: "Afternoon",
//           place: "Vatnajökull National Park",
//           reason: "Hike and enjoy the breathtaking landscapes.",
//         },
//         {
//           time: "Evening",
//           place: "Old Harbour House",
//           reason: "Experience a cozy dining atmosphere with fresh seafood.",
//         },
//       ],
//     },
//     {
//       day: 5,
//       summary: "Departure",
//       items: [
//         {
//           time: "Morning",
//           place: "Reykjavík",
//           reason: "Last-minute shopping and exploring the city.",
//           travel_time_to_next: 68,
//         },
//         {
//           time: "Afternoon",
//           place: "Keflavik International Airport",
//           reason: "Prepare for departure back to Miami.",
//         },
//         {
//           time: "Evening",
//           place: "Flight back to Miami",
//           reason: "Return home after an adventurous trip.",
//         },
//       ],
//     },
//   ],
//   budget: {
//     currency: "USD",
//     estimated_total: 2250,
//   },
//   weather: {
//     temperature: "5°C - 15°C",
//     condition: "Clear",
//     description:
//       "Mild weather with clear skies, ideal for Northern Lights viewing.",
//   },
//   generated_at: "2025-12-07T15:50:40.706291Z",
//   version: 1,
//   destination_image_url:
//     "https://images.unsplash.com/photo-1680766285771-6505e645d92f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w4NDA0MzN8MHwxfHNlYXJjaHwxfHxJY2VsYW5kJTIwdHJhdmVsJTIwbGFuZG1hcmslMjBjaXR5fGVufDB8MHx8fDE3NjUxMjI1Mjd8MA&ixlib=rb-4.1.0&q=80&w=1080&w=2000&h=1200&fit=crop",
//   flight_options: [
//     {
//       option_id: 1,
//       type: "outbound",
//       airline: "Airline SK",
//       airline_code: "SK",
//       flight_number: "SK958",
//       departure_airport: "MIA",
//       departure_time: "2025-12-10T19:55:00",
//       arrival_airport: "KEF",
//       arrival_time: "2025-12-11T15:15:00",
//       duration: "14h 20m",
//       stops: 1,
//       price: 411.415,
//       currency: "USD",
//     },
//     {
//       option_id: 1,
//       type: "return",
//       airline: "Airline SK",
//       airline_code: "SK",
//       flight_number: "SK596",
//       departure_airport: "KEF",
//       departure_time: "2025-12-15T11:30:00",
//       arrival_airport: "MIA",
//       arrival_time: "2025-12-16T18:05:00",
//       duration: "35h 35m",
//       stops: 1,
//       price: 411.415,
//       currency: "USD",
//     },
//   ],
//   flights: {
//     arrival: {
//       origin: "Miami (MIA)",
//       destination: "Iceland (KEF)",
//       airline: "Airline SK (SK958)",
//       departure_time: "07:55 PM",
//       arrival_time: "03:15 PM",
//       date: "2025-12-10",
//       cost: 411,
//       currency: "USD",
//       notes: "Flight duration: 14h 20m. 1 stop(s)",
//     },
//     departure: {
//       origin: "Iceland (KEF)",
//       destination: "Miami (MIA)",
//       airline: "Airline SK (SK596)",
//       departure_time: "11:30 AM",
//       arrival_time: "06:05 PM",
//       date: "2025-12-15",
//       cost: 411,
//       currency: "USD",
//       notes: "Flight duration: 35h 35m. 1 stop(s)",
//     },
//   },
//   flight_total_cost: 822.83,
// };

export function ChatInterface() {
  // Load initial state from localStorage or use defaults/mock data
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem('voyageai_messages');
    return saved ? JSON.parse(saved) : [];
  });
  const [streamingMessage, setStreamingMessage] = useState<string>("");
  const [plan, setPlan] = useState<Plan | null>(() => {
    const saved = localStorage.getItem('voyageai_plan');
    return saved ? JSON.parse(saved) : null;
  });
  const [planText, setPlanText] = useState<string>("");
  const [status, setStatus] = useState<string>("idle");
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentNode, setCurrentNode] = useState<string>("");
  const [isPlanMode, setIsPlanMode] = useState(false);
  const [userRequest, setUserRequest] = useState<UserRequest | null>(() => {
    const saved = localStorage.getItem('voyageai_userRequest');
    return saved ? JSON.parse(saved) : null;
  });
  const [constraints, setConstraints] = useState<Constraints | null>(() => {
    const saved = localStorage.getItem('voyageai_constraints');
    return saved ? JSON.parse(saved) : null;
  });
  const [subTasks, setSubTasks] = useState<string[]>([]);
  const [currentSubTaskIndex, setCurrentSubTaskIndex] = useState<number>(0);
  const [completedTasksCount, setCompletedTasksCount] = useState<number>(0);

  // Background settings - default to Road Trip image
  const [showSettings, setShowSettings] = useState(false);
  const [bgType, setBgType] = useState<"solid" | "image" | "slideshow">(() => {
    const saved = localStorage.getItem('voyageai_bgType');
    return (saved as "solid" | "image" | "slideshow") || "image";
  });
  const [selectedColorIndex, setSelectedColorIndex] = useState(() => {
    const saved = localStorage.getItem('voyageai_selectedColorIndex');
    return saved ? parseInt(saved) : 0;
  });
  const [selectedImageIndex, setSelectedImageIndex] = useState(() => {
    const saved = localStorage.getItem('voyageai_selectedImageIndex');
    return saved ? parseInt(saved) : 0;
  });
  const [currentBgIndex, setCurrentBgIndex] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('voyageai_messages', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (plan) {
      localStorage.setItem('voyageai_plan', JSON.stringify(plan));
    }
  }, [plan]);

  useEffect(() => {
    if (userRequest) {
      localStorage.setItem('voyageai_userRequest', JSON.stringify(userRequest));
    }
  }, [userRequest]);

  useEffect(() => {
    if (constraints) {
      localStorage.setItem('voyageai_constraints', JSON.stringify(constraints));
    }
  }, [constraints]);

  useEffect(() => {
    localStorage.setItem('voyageai_bgType', bgType);
  }, [bgType]);

  useEffect(() => {
    localStorage.setItem('voyageai_selectedColorIndex', selectedColorIndex.toString());
  }, [selectedColorIndex]);

  useEffect(() => {
    localStorage.setItem('voyageai_selectedImageIndex', selectedImageIndex.toString());
  }, [selectedImageIndex]);

  // Rotate background images when slideshow is enabled
  useEffect(() => {
    if (bgType !== "slideshow") return;

    const interval = setInterval(() => {
      setCurrentBgIndex((prev) => (prev + 1) % BACKGROUND_IMAGES.length);
    }, 10000); // Change every 10 seconds

    return () => clearInterval(interval);
  }, [bgType]);

  // Calculate Must-Haves from plan
  const mustHaves = useMemo(() => generateMustHaves(plan), [plan]);

  // Get current background style
  const getBackgroundStyle = () => {
    if (bgType === "solid") {
      return { backgroundColor: SOLID_COLORS[selectedColorIndex].value };
    } else if (bgType === "image") {
      return {
        backgroundImage: `url(${BACKGROUND_IMAGES[selectedImageIndex].url})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      };
    } else {
      // slideshow
      return {
        backgroundImage: `url(${BACKGROUND_IMAGES[currentBgIndex].url})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        transition: "background-image 1s ease-in-out",
      };
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSendMessage = async (message: string) => {
    // Add user message immediately
    const userMessage: Message = {
      role: "human",
      content: message,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setStatus("processing");
    setCurrentNode("");
    setPlanText(""); // Reset plan text for new request
    setStreamingMessage(" "); // Set to space to trigger display (truthy value)
    setIsPlanMode(false); // Will be set to true if we detect plan-making nodes

    await apiClient.streamChat(
      message,
      (event: StreamEvent) => {
        // Debug logging
        if (
          event.node === "synthesize_plan" ||
          event.node === "validate_plan" ||
          event.node === "chat"
        ) {
          console.log(`📥 Frontend received event from node: ${event.node}`);
          console.log(`   Status: ${event.status}`);
          if (event.chat_chunk) {
            console.log(
              `   Chat chunk: ${event.chat_chunk.substring(0, 30)}...`
            );
          }
        }

        // Handle streaming chat text
        if (event.chat_text) {
          setStreamingMessage(event.chat_text);
        }

        // Handle chat completion
        if (event.chat_complete) {
          setStreamingMessage("");
          // Messages will be updated from event.messages
        }

        // Update messages immediately when they arrive
        if (event.messages && event.messages.length > 0) {
          // Force update when entering plan nodes to ensure chat confirmation message is shown
          if (event.node === "normalize_input" || event.node === "chat") {
            console.log(`📨 Force updating messages from node: ${event.node}`);
            setMessages(event.messages);
            if (!event.chat_text && event.node === "normalize_input") {
              setStreamingMessage("");
            }
          } else {
            // Only update if messages actually changed (to avoid unnecessary re-renders)
            setMessages((prev) => {
              if (JSON.stringify(prev) !== JSON.stringify(event.messages)) {
                // Clear streamingMessage if we got new complete messages
                if (!event.chat_text) {
                  setStreamingMessage("");
                }
                return event.messages;
              }
              return prev;
            });
          }
        }

        // Handle streaming plan text
        if (event.plan_text) {
          setPlanText(event.plan_text);
        }

        // Update final plan (JSON)
        if (event.plan) {
          console.log("✅ Setting plan:", event.plan);
          setPlan(event.plan);
        }

        // Update status
        if (event.status) {
          setStatus(event.status);
        }

        // Update validation errors
        if (event.validation_errors) {
          setValidationErrors(event.validation_errors);
        }

        // Update current node
        if (event.node) {
          const prevNode = currentNode;
          setCurrentNode(event.node);

          // Detect if we're in plan-making mode
          const planNodes = [
            "create_plan",
            "synthesize_plan",
            "validate_plan",
            "coordinator",
            "judge",
            "normalize_input",
            "decompose_task",
            "execute_tool",
          ];
          const chatNodes = ["chat"];

          // If we just left chat node and entered a plan node
          if (chatNodes.includes(prevNode) && planNodes.includes(event.node)) {
            console.log(
              `🔄 Transitioning from ${prevNode} to ${event.node} - clearing streaming message`
            );
            setIsPlanMode(true);
            // Clear streaming message to show completed chat messages
            setStreamingMessage("");
            // Then immediately reset to show plan progress
            setTimeout(() => {
              setStreamingMessage(" ");
            }, 100);
          } else if (planNodes.includes(event.node)) {
            setIsPlanMode(true);
            // Show streaming message during plan making
            if (!streamingMessage || streamingMessage.trim().length > 0) {
              setStreamingMessage(" "); // Reset to show typing indicator
            }
          }
        }

        // Update user_request and constraints
        if (event.user_request) {
          console.log("📋 Setting user_request:", event.user_request);
          setUserRequest(event.user_request);
        }
        if (event.constraints) {
          console.log("📋 Setting constraints:", event.constraints);
          setConstraints(event.constraints);
        }

        // Update subtask progress
        if (event.sub_tasks) {
          setSubTasks(event.sub_tasks);
        }
        if (event.current_sub_task_index !== undefined) {
          setCurrentSubTaskIndex(event.current_sub_task_index);
        }
        if (event.completed_tasks_count !== undefined) {
          setCompletedTasksCount(event.completed_tasks_count);
        }

        // Handle errors
        if (event.error) {
          console.error("Stream error:", event.error);
        }
      },
      (error: Error) => {
        console.error("Streaming error:", error);
        setStatus("error");
        setIsStreaming(false);
      },
      () => {
        console.log("🏁 Stream completed");
        setIsStreaming(false);
        setStatus("completed");
        setCurrentNode("");
        setStreamingMessage("");
      }
    );
  };

  const handleReset = () => {
    // Abort any ongoing stream
    apiClient.abortStream();

    // Reset session
    apiClient.resetSession();

    // Clear all state
    setMessages([]);
    setStreamingMessage("");
    setPlan(null);
    setPlanText("");
    setStatus("idle");
    setValidationErrors([]);
    setCurrentNode("");
    setIsStreaming(false);
    setIsPlanMode(false);
    setUserRequest(null);
    setConstraints(null);
    setSubTasks([]);
    setCurrentSubTaskIndex(0);
    setCompletedTasksCount(0);
  };

  return (
    <div
      className="h-screen w-full font-sans text-gray-800 relative flex items-center justify-center p-4"
      style={getBackgroundStyle()}
    >
      {/* Background overlay for better contrast (only for images) */}
      {bgType !== "solid" && (
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900/30 to-gray-800/40"></div>
      )}

      {/* Main Container - Card Style */}
      <div className="relative z-10 flex flex-col h-full w-full max-w-7xl shadow-2xl bg-white/40 backdrop-blur-xl rounded-3xl overflow-hidden border border-white/60 ring-1 ring-white/50">
        {/* Header */}
        <header className="h-16 border-b border-white/50 bg-white/60 backdrop-blur-md flex items-center justify-between px-6 shrink-0 z-20">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg overflow-hidden">
              <img
                src="/Logo.png"
                alt="VoyageAI Logo"
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <h1 className="font-bold text-gray-800 text-lg tracking-tight leading-tight">
                VoyageAI <span className="text-teal-600">Planner</span>
              </h1>
              <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">
                Premium Concierge
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 hover:bg-white/50 rounded-full transition-colors text-gray-500 hover:text-teal-600"
              title="Background Settings"
            >
              <Settings size={20} />
            </button>
            <button
              onClick={handleReset}
              className="p-2 hover:bg-white/50 rounded-full transition-colors text-gray-500 hover:text-teal-600"
              title="Reset Session"
            >
              <RotateCcw size={18} />
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden relative">
          {/* LEFT COLUMN: CHAT INTERFACE */}
          <div className="w-full md:w-[380px] flex flex-col border-r border-gray-200 bg-white/70 backdrop-blur-md shrink-0 h-full">
            <div className="flex-1 overflow-y-auto">
              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                currentNode={currentNode}
                isPlanMode={isPlanMode}
              />
              <div ref={messagesEndRef} />

              {/* Trending Now - Only show when no messages */}
              {messages.length === 0 && !isStreaming && (
                <div className="px-4 pb-4">
                  <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">
                    Trending Now
                  </h2>
                  <div className="grid grid-cols-1 gap-3 mb-4">
                    {SUGGESTED_TRIPS.slice(0, 3).map((trip) => (
                      <div
                        key={trip.id}
                        onClick={() => handleSendMessage(trip.prompt)}
                        className="flex gap-3 p-3 bg-white/60 backdrop-blur-sm rounded-xl border border-white/80 hover:bg-white hover:shadow-lg hover:scale-[1.02] transition-all duration-300 cursor-pointer group"
                      >
                        <div className="relative w-12 h-12 rounded-lg overflow-hidden shrink-0">
                          <img
                            src={trip.image}
                            alt={trip.title}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                          />
                        </div>
                        <div className="flex-1 flex flex-col justify-center text-left">
                          <h4 className="font-bold text-gray-800 text-xs group-hover:text-teal-600 transition-colors mb-1">
                            {trip.title}
                          </h4>
                          <p className="text-[10px] text-gray-500 flex items-center gap-1">
                            <MapPin size={10} className="text-teal-500" />
                            {trip.subtitle}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <InputBox onSend={handleSendMessage} disabled={isStreaming} />
          </div>

          {/* RIGHT COLUMN: ITINERARY VIEW & SIDEBAR */}
          <div className="flex flex-1 overflow-hidden relative">
            {/* Main Content Area (Itinerary View) */}
            <main className="flex-1 flex flex-col relative z-10 transition-all duration-300 overflow-hidden">
              <PlanDisplay
                plan={plan}
                planText={planText}
                validationErrors={validationErrors}
                status={status}
                currentNode={currentNode}
                isProcessing={isStreaming}
                userRequest={userRequest}
                constraints={constraints}
                subTasks={subTasks}
                currentSubTaskIndex={currentSubTaskIndex}
                completedTasksCount={completedTasksCount}
              />
            </main>

            {/* Right Sidebar (Trip Wallet) */}
            <aside className="w-72 lg:w-80 bg-white/80 backdrop-blur-2xl border-l border-white/50 overflow-y-auto shadow-2xl">
              <div className="p-6 flex flex-col">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest">
                    TRIP WALLET
                  </h2>
                </div>

                {/* Trip Summary Card - Show when we have user request */}
                {plan || userRequest ? (
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_10px_30px_-5px_rgba(0,0,0,0.05)] overflow-hidden relative mb-6">
                    <div className="h-2 bg-pink-500 w-full top-0 absolute"></div>
                    <div className="p-5">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
                            Destination
                          </div>
                          <h3 className="font-bold text-2xl text-gray-800">
                            {plan?.destination?.split(",")[0] ||
                              userRequest?.destination ||
                              "Planning..."}
                          </h3>
                        </div>
                        {(plan?.constraints?.travelers ||
                          constraints?.travelers) && (
                          <div className="text-right">
                            <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
                              Travelers
                            </div>
                            <div className="font-bold text-lg text-gray-800 flex items-center justify-end gap-1">
                              <Users size={16} className="text-teal-500" />
                              {plan?.constraints?.travelers ||
                                constraints?.travelers}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="space-y-4">
                        {(plan?.constraints?.start_date ||
                          constraints?.start_date) && (
                          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                            <div className="bg-white p-2 rounded-lg text-pink-600 shadow-sm">
                              <Calendar size={18} />
                            </div>
                            <div>
                              <div className="text-[10px] text-gray-400 uppercase font-bold">
                                Dates
                              </div>
                              <div className="text-sm font-semibold text-gray-700">
                                {plan?.constraints?.start_date ||
                                  constraints?.start_date}{" "}
                                -{" "}
                                {plan?.constraints?.end_date ||
                                  constraints?.end_date}
                              </div>
                            </div>
                          </div>
                        )}

                        {(plan?.budget?.estimated_total ||
                          constraints?.budget_limit) && (
                          <div className="p-3 bg-gray-50 rounded-xl">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-[10px] text-gray-400 uppercase font-bold">
                                BUDGET
                              </span>
                              {plan?.budget?.estimated_total &&
                                constraints?.budget_limit && (
                                  <span className="text-xs font-bold text-teal-700">
                                    {Math.round(
                                      (plan.budget.estimated_total /
                                        constraints.budget_limit) *
                                        100
                                    )}
                                    %
                                  </span>
                                )}
                            </div>
                            {plan?.budget?.estimated_total &&
                            constraints?.budget_limit ? (
                              <>
                                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-teal-500 rounded-full transition-all duration-1000 ease-out"
                                    style={{
                                      width: `${Math.min(
                                        100,
                                        (plan.budget.estimated_total /
                                          constraints.budget_limit) *
                                          100
                                      )}%`,
                                    }}
                                  ></div>
                                </div>
                                <div className="flex justify-between mt-2 text-xs">
                                  <span className="text-gray-500">
                                    {plan.budget.currency ||
                                      constraints.currency ||
                                      "$"}
                                    {plan.budget.estimated_total.toLocaleString()}
                                  </span>
                                  <span className="text-gray-400">
                                    Limit: {constraints.currency || "$"}
                                    {constraints.budget_limit.toLocaleString()}
                                  </span>
                                </div>
                              </>
                            ) : constraints?.budget_limit ? (
                              <div className="text-sm font-semibold text-gray-700">
                                {constraints.currency || "$"}
                                {constraints.budget_limit.toLocaleString()}{" "}
                                limit
                              </div>
                            ) : (
                              <div className="text-sm font-semibold text-gray-700">
                                {plan?.budget?.currency || "$"}
                                {plan?.budget?.estimated_total?.toLocaleString() ||
                                  "N/A"}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Flight Cost */}
                        {plan?.flight_total_cost && (
                          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                            <div className="bg-white p-2 rounded-lg text-blue-600 shadow-sm">
                              <Plane size={18} />
                            </div>
                            <div className="flex-1">
                              <div className="text-[10px] text-gray-400 uppercase font-bold">
                                Flights
                              </div>
                              <div className="text-sm font-semibold text-gray-700">
                                {plan.budget?.currency || "$"}
                                {Math.round(
                                  plan.flight_total_cost
                                ).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Placeholder Card when no plan */
                  <div className="bg-white rounded-2xl border border-dashed border-gray-300 overflow-hidden relative mb-6">
                    <div className="p-8">
                      <div className="flex flex-col items-center justify-center text-center space-y-3">
                        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
                          <MapPin size={32} className="text-gray-300" />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-gray-400 mb-1">
                            No Trip Yet
                          </div>
                          <div className="text-xs text-gray-300">
                            Start planning your adventure
                          </div>
                        </div>
                        {/* Skeleton placeholders */}
                        <div className="w-full space-y-2 pt-4">
                          <div className="h-3 bg-gray-100 rounded-full w-3/4 mx-auto"></div>
                          <div className="h-3 bg-gray-100 rounded-full w-1/2 mx-auto"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Must-Haves Section */}
                {mustHaves.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">
                      Must-Haves
                    </h3>
                    <div className="space-y-3">
                      {mustHaves.map((item, idx) => {
                        const iconMap: Record<string, any> = {
                          nature: Leaf,
                          culture: Landmark,
                          food: Utensils,
                          sightseeing: Camera,
                        };
                        const Icon = iconMap[item.icon] || Camera;

                        return (
                          <div
                            key={idx}
                            className="flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all"
                          >
                            <div className="w-10 h-10 rounded-lg bg-pink-100 flex items-center justify-center text-pink-600 shrink-0">
                              <Icon size={18} />
                            </div>
                            <div className="flex-1">
                              <div className="text-xs font-bold text-gray-700">
                                {item.interest}
                              </div>
                              <div className="text-[10px] text-gray-400">
                                {item.description}
                              </div>
                            </div>
                            <CheckCircle2 size={16} className="text-teal-500" />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Progress indicator when processing */}
                {isStreaming && !plan && (
                  <div className="text-center text-gray-400 mt-12">
                    <Compass size={24} className="mx-auto mb-2 animate-spin" />
                    <p className="text-sm">Creating your plan...</p>
                    <p className="text-xs mt-1">
                      {currentNode && `Step: ${currentNode}`}
                    </p>
                  </div>
                )}

                {/* Empty state */}
                {!plan && !userRequest && !isStreaming && (
                  <div className="text-center text-gray-400 m-12">
                    <MapPin size={24} className="mx-auto mb-2" />
                    <p className="text-sm">No Itinerary Data</p>
                    <p className="text-xs">
                      Create a plan in the chat on the left
                    </p>
                  </div>
                )}

                {/* Spacer to push Quick Links to bottom */}
                <div className="flex-1"></div>

                {/* Quick Links Section - Always at Bottom */}
                <div className="pt-6 mt-6 border-t border-gray-200 shrink-0">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">
                    Quick Links
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <a
                      href="https://www.google.com/flights"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:scale-105 transition-all group"
                    >
                      <div className="w-12 h-12 mb-2 flex items-center justify-center">
                        <img
                          src="https://www.google.com/images/branding/googleg/1x/googleg_standard_color_128dp.png"
                          alt="Google Flights"
                          className="w-10 h-10 object-contain"
                        />
                      </div>
                      <div className="text-[11px] font-bold text-gray-700 text-center">
                        Google Flights
                      </div>
                    </a>

                    <a
                      href="https://www.booking.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:scale-105 transition-all group"
                    >
                      <div className="w-12 h-12 mb-2 flex items-center justify-center">
                        <img
                          src="https://cdn.brandfetch.io/id9mEmLNcV/w/400/h/400/theme/dark/icon.jpeg?c=1bxid64Mup7aczewSAYMX&t=1725855381233"
                          alt="Booking.com"
                          className="w-10 h-10 object-contain"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://logo.clearbit.com/booking.com";
                          }}
                        />
                      </div>
                      <div className="text-[11px] font-bold text-gray-700 text-center">
                        Booking.com
                      </div>
                    </a>

                    <a
                      href="https://www.tripadvisor.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:scale-105 transition-all group"
                    >
                      <div className="w-12 h-12 mb-2 flex items-center justify-center">
                        <img
                          src="https://cdn.brandfetch.io/idAnDTFapY/w/400/h/400/theme/dark/icon.jpeg?c=1bfwsmEH20zzEfSNTed"
                          alt="TripAdvisor"
                          className="w-10 h-10 object-contain"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://logo.clearbit.com/tripadvisor.com";
                          }}
                        />
                      </div>
                      <div className="text-[11px] font-bold text-gray-700 text-center">
                        TripAdvisor
                      </div>
                    </a>

                    <a
                      href="https://www.lonelyplanet.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:scale-105 transition-all group"
                    >
                      <div className="w-12 h-12 mb-2 flex items-center justify-center">
                        <img
                          src="https://cdn.brandfetch.io/idiI3E9kfy/w/719/h/719/theme/dark/icon.png?c=1bxid64Mup7aczewSAYMX&t=1759201246606"
                          alt="Lonely Planet"
                          className="w-10 h-10 object-contain"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://logo.clearbit.com/lonelyplanet.com";
                          }}
                        />
                      </div>
                      <div className="text-[11px] font-bold text-gray-700 text-center">
                        Lonely Planet
                      </div>
                    </a>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings size={24} className="text-teal-600" />
                <h2 className="text-xl font-bold text-gray-800">
                  Background Settings
                </h2>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* Background Type Selection */}
              <div>
                <h3 className="text-sm font-bold text-gray-700 mb-3">
                  Background Type
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => setBgType("solid")}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      bgType === "solid"
                        ? "border-teal-500 bg-teal-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-2xl mb-2">🎨</div>
                      <div className="text-sm font-semibold">Solid Color</div>
                    </div>
                  </button>
                  <button
                    onClick={() => setBgType("image")}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      bgType === "image"
                        ? "border-teal-500 bg-teal-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-2xl mb-2">🖼️</div>
                      <div className="text-sm font-semibold">Image</div>
                    </div>
                  </button>
                  <button
                    onClick={() => setBgType("slideshow")}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      bgType === "slideshow"
                        ? "border-teal-500 bg-teal-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-2xl mb-2">🎞️</div>
                      <div className="text-sm font-semibold">Slideshow</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Solid Colors */}
              {bgType === "solid" && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-3">
                    Choose Color
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {SOLID_COLORS.map((color, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedColorIndex(idx)}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          selectedColorIndex === idx
                            ? "border-teal-500 ring-2 ring-teal-200"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                        style={{ backgroundColor: color.value }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-gray-700">
                            {color.name}
                          </span>
                          {selectedColorIndex === idx && (
                            <Check size={18} className="text-teal-600" />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Images */}
              {bgType === "image" && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-3">
                    Choose Image
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    {BACKGROUND_IMAGES.map((img, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedImageIndex(idx)}
                        className={`relative rounded-xl overflow-hidden border-4 transition-all ${
                          selectedImageIndex === idx
                            ? "border-teal-500 ring-2 ring-teal-200"
                            : "border-transparent hover:border-gray-300"
                        }`}
                      >
                        <img
                          src={img.url}
                          alt={img.name}
                          className="w-full h-32 object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-3">
                          <span className="text-white text-sm font-semibold">
                            {img.name}
                          </span>
                          {selectedImageIndex === idx && (
                            <Check
                              size={20}
                              className="absolute top-2 right-2 text-white bg-teal-500 rounded-full p-1"
                            />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Slideshow Info */}
              {bgType === "slideshow" && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">ℹ️</div>
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-1">
                        Automatic Slideshow
                      </h4>
                      <p className="text-sm text-blue-700">
                        Background images will automatically rotate every 10
                        seconds, showcasing all {BACKGROUND_IMAGES.length}{" "}
                        beautiful travel photos.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end">
              <button
                onClick={() => setShowSettings(false)}
                className="px-6 py-2 bg-teal-600 text-white rounded-lg font-semibold hover:bg-teal-700 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
