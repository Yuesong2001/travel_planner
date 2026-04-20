import { Plane, Clock, DollarSign } from "lucide-react";

interface FlightCardProps {
  title: string;
  flight: {
    origin: string; // e.g., "San Francisco (SFO)"
    destination: string; // e.g., "Tokyo (NRT)"
    airline: string; // e.g., "United Airlines (UA875)"
    departure_time: string; // e.g., "08:00 AM"
    arrival_time: string; // e.g., "04:00 PM"
    date: string; // e.g., "2025-04-01"
    cost: number; // Price in USD or local currency
    currency?: string; // e.g., "USD", "JPY"
    notes?: string; // Optional travel notes
  };
}

export function FlightCard({ title, flight }: FlightCardProps) {
  if (!flight) return null;

  const {
    origin,
    destination,
    airline,
    departure_time,
    arrival_time,
    date,
    cost,
    currency = "USD",
    notes,
  } = flight;

  // Format date for display
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // Format currency
  const formatCurrency = (amount: number, curr: string) => {
    if (curr === "JPY" || curr === "KRW") {
      return `¥${amount.toLocaleString()}`;
    } else if (curr === "EUR") {
      return `€${amount.toLocaleString()}`;
    } else if (curr === "GBP") {
      return `£${amount.toLocaleString()}`;
    } else {
      return `$${amount.toLocaleString()}`;
    }
  };

  return (
    <div className="bg-white p-5 rounded-xl border border-blue-100 shadow-lg mb-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 border-b border-gray-100 pb-3">
        <h3 className="text-lg font-extrabold text-blue-600 flex items-center gap-2">
          <Plane size={20} /> {title} Flight
        </h3>
        <div className="text-xs font-semibold text-gray-500">
          {formatDate(date)}
        </div>
      </div>

      {/* Flight Route */}
      <div className="flex items-center justify-between">
        {/* Origin */}
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">
            {origin.split(" ")[0]}
          </div>
          <div className="text-sm text-gray-500">
            {origin.match(/\(([^)]+)\)/)?.[1] || origin.split(" ")[1]}
          </div>
        </div>

        {/* Route Line with Airline */}
        <div className="flex flex-col items-center flex-1 mx-4">
          <div className="w-full h-0.5 bg-blue-200 relative">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-blue-400"></div>
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-blue-600"></div>
          </div>
          <div className="text-xs text-blue-500 font-medium mt-1">
            {airline}
          </div>
        </div>

        {/* Destination */}
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">
            {destination.split(" ")[0]}
          </div>
          <div className="text-sm text-gray-500">
            {destination.match(/\(([^)]+)\)/)?.[1] || destination.split(" ")[1]}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="mt-5 pt-4 border-t border-gray-100 grid grid-cols-2 gap-4 text-sm">
        <div className="flex items-center gap-2 text-gray-700">
          <Clock size={16} className="text-teal-500" />
          <span className="font-semibold">{departure_time}</span> -{" "}
          {arrival_time}
        </div>
        <div className="flex items-center gap-2 text-right justify-end text-gray-700">
          <DollarSign size={16} className="text-pink-500" />
          <span className="font-semibold">
            {formatCurrency(cost, currency)}
          </span>
        </div>
      </div>

      {/* Notes (if present) */}
      {notes && (
        <p className="mt-3 text-xs text-gray-500 italic p-2 bg-gray-50 rounded-lg border border-gray-100">
          <strong>Note:</strong> {notes}
        </p>
      )}
    </div>
  );
}
