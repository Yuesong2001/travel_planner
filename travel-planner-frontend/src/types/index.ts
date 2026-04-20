export interface Message {
  role: string;
  content: string;
}

export interface FlightOption {
  option_id: number;
  type: "outbound" | "return";
  airline: string;
  airline_code: string;
  flight_number: string;
  departure_airport: string;
  departure_time: string;  // ISO 8601 format
  arrival_airport: string;
  arrival_time: string;
  duration: string;  // e.g., "14h 30m"
  stops: number;
  price: number;
  currency: string;
}

export interface FlightDetails {
  origin: string;
  destination: string;
  airline: string;
  departure_time: string;
  arrival_time: string;
  date: string;
  cost: number;
  currency?: string;
  notes?: string;
}

export interface Plan {
  destination: string;
  destination_image_url?: string;
  constraints: {
    origin?: string;  // NEW: Departure location for flight search
    budget_limit?: number | null;
    currency?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    interests?: string[];
    travelers?: number | null;
    travel_type?: string | null;
  };
  days: Array<{
    day: number;
    summary: string;
    items: Array<{
      time: string;
      place: string;
      reason: string;
      type?: string;
      travel_time_to_next?: number; // in minutes
    }>;
  }>;
  budget: {
    currency?: string | null;
    estimated_total?: number | null;
  };
  weather?: {
    temperature?: string | null;
    condition?: string | null;
    description?: string | null;
  };
  flight_options?: FlightOption[];  // Full list of flight options
  flights?: {  // NEW: Formatted for FlightCard component (frontendexample.jsx structure)
    arrival?: FlightDetails;
    departure?: FlightDetails;
  };
  flight_total_cost?: number;  // Total flight cost (cheapest combination)
  generated_at: string;
  version: number;
}

export interface UserRequest {
  destination?: string;
  duration?: string;
  month?: string;
  budget?: string;
  travelers?: number;
  interests?: string[];
  [key: string]: any;
}

export interface Constraints {
  budget_limit?: number | null;
  currency?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  interests?: string[];
  travelers?: number | null;
  travel_type?: string | null;
  [key: string]: any;
}

export interface StreamEvent {
  messages: Message[];
  plan: Plan | null;
  ai_response: string;
  status: string;
  validation_errors?: string[];
  timestamp: string;
  node?: string;
  session_id?: string;
  error?: string;
  plan_chunk?: string;
  plan_text?: string;
  chat_chunk?: string;
  chat_text?: string;
  chat_complete?: boolean;
  user_request?: UserRequest;
  constraints?: Constraints;
  sub_tasks?: string[];
  current_sub_task_index?: number;
  completed_tasks_count?: number;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
}
