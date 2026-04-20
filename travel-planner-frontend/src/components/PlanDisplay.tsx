import React, { useState } from "react";
import {
  Calendar,
  MapPin,
  Hotel,
  Plane,
  Compass,
  Loader2,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  Users,
  Cloud,
  Sun,
  CloudRain,
  Leaf,
  Landmark,
  Camera,
  BookOpen,
  Utensils,
  List,
  Map as MapIcon,
  ArrowRight,
  MoreHorizontal,
} from "lucide-react";
import { FlightCard } from "./FlightCard";
import type { Plan, UserRequest, Constraints } from "../types";

interface PlanDisplayProps {
  plan: Plan | null;
  planText?: string;
  validationErrors?: string[];
  status: string;
  currentNode?: string;
  isProcessing?: boolean;
  userRequest?: UserRequest | null;
  constraints?: Constraints | null;
  subTasks?: string[];
  currentSubTaskIndex?: number;
  completedTasksCount?: number;
}

// Background images for destinations - using direct Unsplash photo URLs
const BACKGROUNDS: Record<string, string> = {
  // Default travel background
  default:
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&q=80&w=2021",

  // Popular destinations with curated photos
  tokyo:
    "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&q=80&w=2021",
  paris:
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&q=80&w=2021",
  london:
    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&q=80&w=2021",
  "new york":
    "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&q=80&w=2021",
  rome: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&q=80&w=2021",
  barcelona:
    "https://images.unsplash.com/photo-1562883676-8c7feb83f09b?auto=format&fit=crop&q=80&w=2021",
  dubai:
    "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&q=80&w=2021",
  singapore:
    "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&q=80&w=2021",
  sydney:
    "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&q=80&w=2021",
  bangkok:
    "https://images.unsplash.com/photo-1508009603885-50cf7c579365?auto=format&fit=crop&q=80&w=2021",
  istanbul:
    "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&q=80&w=2021",
  amsterdam:
    "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?auto=format&fit=crop&q=80&w=2021",
  bali: "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&q=80&w=2021",
  iceland:
    "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&q=80&w=2021",
  maldives:
    "https://images.unsplash.com/photo-1514282401047-d79a71a590e8?auto=format&fit=crop&q=80&w=2021",
  hawaii:
    "https://images.unsplash.com/photo-1542259009477-d625272157b7?auto=format&fit=crop&q=80&w=2021",
  switzerland:
    "https://images.unsplash.com/photo-1527004013197-933c4bb611b3?auto=format&fit=crop&q=80&w=2021",
  santorini:
    "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&q=80&w=2021",
  venice:
    "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?auto=format&fit=crop&q=80&w=2021",
  prague:
    "https://images.unsplash.com/photo-1541849546-216549ae216d?auto=format&fit=crop&q=80&w=2021",
};

// Generate background URL based on destination
const getDestinationBackground = (destination?: string): string => {
  if (!destination) return BACKGROUNDS.default;

  // Extract main city/country name (remove extra info after comma)
  const mainLocation = destination.split(",")[0].trim().toLowerCase();

  // Check if we have a curated photo for this destination
  if (BACKGROUNDS[mainLocation]) {
    return BACKGROUNDS[mainLocation];
  }

  // Return default for unknown destinations
  return BACKGROUNDS.default;
};

// Icon mapping for different activity types
const ICON_MAP: Record<string, any> = {
  Park: Leaf,
  Shrine: Landmark,
  Temple: Landmark,
  Dining: Utensils,
  Museum: BookOpen,
  Sightseeing: Camera,
  Tower: Landmark,
  Shopping: MapPin,
  hotel: Hotel,
  flight: Plane,
};

const getIcon = (type: string) => {
  const IconComponent = ICON_MAP[type] || MapPin;
  return <IconComponent size={16} />;
};

// Plan Progress Component (similar to Travel Wallet in frontendexample)
const PlanProgress = ({
  currentNode,
  status,
  subTasks,
  currentSubTaskIndex,
  completedTasksCount,
}: {
  currentNode?: string;
  status: string;
  userRequest?: UserRequest | null;
  constraints?: Constraints | null;
  plan?: Plan | null;
  subTasks?: string[];
  currentSubTaskIndex?: number;
  completedTasksCount?: number;
}) => {
  const getNodeStatus = (nodeName?: string) => {
    const statusMap: Record<
      string,
      { label: string; icon: any; color: string }
    > = {
      determine_intent: {
        label: "Understanding Request",
        icon: Sparkles,
        color: "text-blue-500",
      },
      normalize_input: {
        label: "Organizing Details",
        icon: MapPin,
        color: "text-purple-500",
      },
      decompose_task: {
        label: "Planning Tasks",
        icon: Compass,
        color: "text-purple-500",
      },
      synthesize_plan: {
        label: "Building Itinerary",
        icon: Calendar,
        color: "text-teal-500",
      },
      validate_plan: {
        label: "Validating Details",
        icon: CheckCircle2,
        color: "text-green-500",
      },
      coordinator: {
        label: "Coordinating",
        icon: Clock,
        color: "text-orange-500",
      },
      judge: {
        label: "Reviewing Quality",
        icon: AlertCircle,
        color: "text-indigo-500",
      },
    };

    return (
      statusMap[nodeName || ""] || {
        label: "Processing",
        icon: Loader2,
        color: "text-gray-500",
      }
    );
  };

  const nodeStatus = getNodeStatus(currentNode);
  const IconComponent = nodeStatus.icon;

  return (
    <div className="animate-in slide-in-from-right-4 duration-700">
      {/* Current Progress Card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden relative mb-4">
        <div className="h-2 bg-gradient-to-r from-teal-500 to-emerald-500 w-full top-0 absolute"></div>
        <div className="p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-2 rounded-lg ${nodeStatus.color} bg-opacity-10`}>
              <IconComponent
                size={20}
                className={`${nodeStatus.color} ${
                  currentNode ? "animate-pulse" : ""
                }`}
              />
            </div>
            <div className="flex-1">
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">
                Current Step
              </div>
              <h3 className="font-bold text-gray-800">{nodeStatus.label}</h3>
            </div>
          </div>

          <div className="space-y-2 mt-4 text-xs text-gray-500">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  status === "processing"
                    ? "bg-teal-500 animate-pulse"
                    : "bg-gray-300"
                }`}
              ></div>
              <span>Status: {status}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Subtasks List */}
      {subTasks && subTasks.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">
                Tasks Progress
              </h3>
              <span className="text-xs font-semibold text-teal-600">
                {completedTasksCount || 0} / {subTasks.length}
              </span>
            </div>

            <div className="space-y-2">
              {subTasks.map((task, index) => {
                const isCompleted = (completedTasksCount || 0) > index;
                const isCurrent = (currentSubTaskIndex || 0) === index;

                return (
                  <div
                    key={index}
                    className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
                      isCurrent
                        ? "bg-teal-50 border-2 border-teal-200"
                        : isCompleted
                        ? "bg-gray-50"
                        : "bg-white border border-gray-100"
                    }`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {isCompleted ? (
                        <CheckCircle2 size={16} className="text-teal-500" />
                      ) : isCurrent ? (
                        <Loader2
                          size={16}
                          className="text-teal-500 animate-spin"
                        />
                      ) : (
                        <div className="w-4 h-4 rounded-full border-2 border-gray-300"></div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-xs leading-relaxed ${
                          isCurrent
                            ? "text-teal-700 font-semibold"
                            : isCompleted
                            ? "text-gray-500"
                            : "text-gray-400"
                        }`}
                      >
                        {task}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Activity Item Component
const ActivityItem = ({ item }: { item: any }) => (
  <div className="flex items-start gap-4 p-4 bg-white/70 backdrop-blur-sm rounded-xl border border-pink-100 shadow-sm transition-all hover:shadow-md hover:border-teal-200 cursor-pointer group">
    <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-pink-100 text-pink-600 shadow-inner">
      {getIcon(item.type)}
    </div>
    <div className="flex-1 min-w-0">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-0.5">
        {item.time || "All day"}
      </div>
      <h4 className="font-bold text-gray-800 text-base group-hover:text-teal-600 transition-colors truncate">
        {item.place || item.title}
      </h4>
      {item.reason && (
        <p className="text-gray-500 text-xs mt-1 italic opacity-80">
          {item.reason}
        </p>
      )}

      {/* Actionable buttons */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <a
          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
            item.place || item.title
          )}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center text-xs text-teal-600 hover:text-teal-800 font-medium"
        >
          <MapIcon size={12} className="mr-1" /> Directions
        </a>
        {item.type === "Dining" && (
          <button className="flex items-center text-xs text-indigo-600 hover:text-indigo-800 font-medium">
            <Calendar size={12} className="mr-1" /> Book
          </button>
        )}
        <button className="p-1 rounded-full text-gray-400 hover:bg-gray-100 ml-auto">
          <MoreHorizontal size={14} />
        </button>
      </div>
    </div>
  </div>
);

// Daily Itinerary Card Component (Collapsible)
const DailyItineraryCard = ({ dayData }: { dayData: any }) => {
  const [isOpen, setIsOpen] = useState(dayData.day === 1); // Open day 1 by default

  return (
    <div className="relative mb-8 pt-4 pb-2 group">
      {/* Timeline Separator (Soft Pink Gradient) */}
      <div
        className={`absolute left-5 top-0 w-0.5 h-full bg-gradient-to-b from-pink-300/50 to-pink-50/20 transition-all duration-300 ${
          isOpen ? "opacity-100" : "opacity-50"
        }`}
      ></div>

      <div className="relative pl-12">
        {/* Day Header */}
        <div
          className="flex items-center justify-between cursor-pointer -ml-12 mb-4"
          onClick={() => setIsOpen(!isOpen)}
        >
          {/* Day Number/Date Bubble */}
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-white font-bold text-sm shadow-lg transition-all duration-300 ${
              isOpen
                ? "bg-teal-500 shadow-teal-300 scale-105"
                : "bg-gray-400 shadow-gray-300 scale-100"
            }`}
          >
            {dayData.day}
          </div>

          <div className="flex-1 min-w-0 pr-4 ml-4">
            <div className="text-xs font-medium text-gray-800 uppercase tracking-widest">
              {dayData.date || `Day ${dayData.day}`}
            </div>
            <h3 className="text-lg font-extrabold text-gray-800 truncate">
              {dayData.summary || `Day ${dayData.day} Itinerary`}
            </h3>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={`https://www.google.com/maps/dir/${dayData.items
                ?.map((item: any) =>
                  encodeURIComponent(item.place || item.title)
                )
                .join("/")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold px-3 py-1.5 rounded-full bg-pink-50 text-pink-700 hover:bg-pink-100 transition-colors flex items-center"
              onClick={(e) => e.stopPropagation()}
            >
              <MapIcon size={12} className="mr-1" /> Map
            </a>
            <ArrowRight
              size={18}
              className={`text-gray-500 transition-transform ${
                isOpen ? "rotate-90" : "rotate-0"
              }`}
            />
          </div>
        </div>

        {/* Activity Items (Content) */}
        {isOpen && (
          <div className="space-y-4 pt-2 pb-4 animate-in slide-in-from-top-4 duration-500">
            {dayData.items?.map((item: any, idx: number) => (
              <React.Fragment key={idx}>
                <ActivityItem item={item} />
                {/* Travel Time - use real data if available */}
                {idx < dayData.items.length - 1 && (
                  <div className="flex items-center text-xs text-gray-600 font-medium italic pl-4 gap-2">
                    <Plane size={12} className="rotate-90 text-pink-500" />
                    {item.travel_time_to_next ? (
                      <>
                        <span className="text-pink-600 font-semibold">
                          {item.travel_time_to_next} min
                        </span>
                        <span className="text-gray-700">Travel Time</span>
                      </>
                    ) : (
                      <span className="text-gray-600">
                        Travel time calculating...
                      </span>
                    )}
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export function PlanDisplay({
  plan,
  planText,
  validationErrors,
  status,
  currentNode,
  isProcessing,
  userRequest,
  constraints,
  subTasks,
  currentSubTaskIndex,
  completedTasksCount,
}: PlanDisplayProps) {
  // Debug logging
  console.log("🎨 PlanDisplay render:", {
    hasPlan: !!plan,
    hasPlanText: !!planText,
    status,
    currentNode,
    userRequest,
  });

  // Check if we're in plan-making mode
  const planNodes = [
    "normalize_input",
    "decompose_task",
    "synthesize_plan",
    "validate_plan",
    "coordinator",
    "judge",
    "execute_tool",
  ];
  const isPlanMode = currentNode && planNodes.includes(currentNode);

  // Get destination background image - use API-provided image if available, otherwise fallback to curated list
  const bgImage =
    plan?.destination_image_url || getDestinationBackground(plan?.destination);

  // Calculate duration
  const getDuration = () => {
    if (plan?.constraints?.start_date && plan?.constraints?.end_date) {
      const start = new Date(plan.constraints.start_date);
      const end = new Date(plan.constraints.end_date);
      return (
        Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1
      );
    }
    return null;
  };

  const duration = getDuration();

  // Show progress card only when processing plan-related nodes and no plan yet
  if (isProcessing && !plan && isPlanMode) {
    return (
      <div className="h-full overflow-y-auto p-6 bg-gradient-to-br from-teal-50/30 to-emerald-50/30 scrollbar-hide">
        <PlanProgress
          currentNode={currentNode}
          status={status}
          userRequest={userRequest}
          constraints={constraints}
          plan={plan}
          subTasks={subTasks}
          currentSubTaskIndex={currentSubTaskIndex}
          completedTasksCount={completedTasksCount}
        />

        {planText && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-4">
            <div className="mb-3 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 size={16} className="animate-spin" />
              <span>Building plan...</span>
            </div>
            <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
              {planText}
              <span className="inline-block w-2 h-4 bg-teal-500 animate-pulse ml-1"></span>
            </pre>
          </div>
        )}
      </div>
    );
  }

  // Show empty state if no plan and not processing
  if (!plan) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-teal-50/30 to-emerald-50/30">
        <div className="text-center px-8">
          <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-teal-50 to-emerald-50 rounded-3xl flex items-center justify-center shadow-lg">
            <Compass size={48} className="text-teal-500" />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-800 mb-2">
            Create Your Dream Trip
          </h2>
          <p className="text-gray-500 max-w-sm mb-8">
            Tell me where you want to go, for how long, and your travel
            interests in the chat on the left, and I will generate your first
            itinerary draft!
          </p>
        </div>
      </div>
    );
  }

  // Main Itinerary View - Timeline Style
  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-teal-300/50 scrollbar-track-transparent">
      {/* Hero Banner */}
      <div className="relative h-64 overflow-hidden rounded-b-3xl shadow-xl">
        <img
          src={bgImage}
          alt={plan.destination}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent p-8 flex flex-col justify-end">
          <h2 className="text-4xl font-extrabold text-white drop-shadow-lg mb-2">
            {plan.destination}
          </h2>
          <p className="text-lg text-pink-200 font-medium drop-shadow">
            {plan.constraints?.start_date &&
              new Date(plan.constraints.start_date).toLocaleDateString()}{" "}
            -{" "}
            {plan.constraints?.end_date &&
              new Date(plan.constraints.end_date).toLocaleDateString()}
            {duration && ` (${duration} Days)`}
          </p>
          {plan.constraints?.interests &&
            plan.constraints.interests.length > 0 && (
              <div className="flex gap-3 mt-3 flex-wrap">
                {plan.constraints.interests.map(
                  (interest: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-white/30 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center"
                    >
                      {interest.includes("cherry") ? "🌸" : "✨"}{" "}
                      {interest.toUpperCase()}
                    </span>
                  )
                )}
              </div>
            )}
        </div>
      </div>

      {/* Sticky Header: Weather, Travelers & Budget */}
      <div className="sticky top-0 z-20 bg-white/90 backdrop-blur-md shadow-lg py-3 px-6 flex justify-between items-center border-b border-gray-100">
        <div className="flex items-center gap-4">
          {plan.weather && (
            <div className="flex items-center gap-1.5 text-teal-600 font-semibold text-xs">
              {plan.weather.condition?.toLowerCase().includes("rain") ? (
                <CloudRain
                  size={16}
                  className="text-blue-400 fill-blue-400/50"
                />
              ) : plan.weather.condition?.toLowerCase().includes("cloud") ? (
                <Cloud size={16} className="text-gray-400 fill-gray-400/50" />
              ) : (
                <Sun size={16} className="text-orange-400 fill-orange-400/50" />
              )}
              <span>{plan.weather.temperature}</span>
            </div>
          )}
          {plan.constraints?.travelers && (
            <div className="flex items-center gap-1.5 text-gray-600 font-semibold text-xs">
              <Users size={14} /> <span>{plan.constraints.travelers}</span>
            </div>
          )}
        </div>

        {/* Budget Meter */}
        {plan.budget?.estimated_total && (
          <div className="flex items-center gap-2 text-gray-700">
            <span className="text-[10px] text-gray-500 uppercase font-bold">
              Budget:
            </span>
            <span className="text-sm font-extrabold text-teal-600">
              {plan.budget.currency || "$"}
              {plan.budget.estimated_total.toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* Flight Information Section */}
      {plan.flights && (plan.flights.arrival || plan.flights.departure) && (
        <div className="px-6 py-4">
          {plan.flights.arrival && (
            <FlightCard title="Arrival" flight={plan.flights.arrival} />
          )}
          {plan.flights.departure && (
            <FlightCard title="Departure" flight={plan.flights.departure} />
          )}
        </div>
      )}

      {/* Validation Errors */}
      {validationErrors && validationErrors.length > 0 && (
        <div className="mx-6 mt-6 p-5 bg-gradient-to-r from-red-50 to-rose-50 border-2 border-red-200 rounded-2xl shadow-sm">
          <div className="flex items-center mb-3">
            <span className="text-2xl mr-2">⚠️</span>
            <h3 className="font-bold text-red-800 text-lg">
              Validation Issues
            </h3>
          </div>
          <ul className="space-y-2">
            {validationErrors.map((error, idx) => (
              <li key={idx} className="flex items-start">
                <span className="text-red-500 mr-2">•</span>
                <span className="text-red-700 text-sm">{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Itinerary Micro View - Vertical Timeline */}
      <div className="p-6 max-w-4xl mx-auto">
        <h3 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2 border-b border-pink-100 pb-2">
          <List size={24} className="text-teal-600" /> Detailed Itinerary
        </h3>
        {plan.days &&
          plan.days.map((dayData: any) => (
            <DailyItineraryCard key={dayData.day} dayData={dayData} />
          ))}

        {/* Raw JSON View - Collapsible */}
        <details className="mt-8">
          <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-800 bg-white px-4 py-3 rounded-xl border border-gray-200 hover:shadow-md transition-all duration-200 flex items-center gap-2">
            <span className="text-lg">🔍</span>
            <span>View Raw JSON Data</span>
          </summary>
          <div className="mt-3 p-4 bg-gray-900 text-green-400 rounded-xl text-xs overflow-x-auto shadow-lg border border-gray-700">
            <pre className="whitespace-pre-wrap break-words">
              {JSON.stringify(plan, null, 2)}
            </pre>
          </div>
        </details>
      </div>
    </div>
  );
}
