import { useState, type FormEvent } from "react";
import { Send, Sparkles } from "lucide-react";

interface InputBoxProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function InputBox({ onSend, disabled }: InputBoxProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput("");
    }
  };

  const quickPrompts = [
    { text: "🗼 Plan Paris Trip", query: "Plan a 5-day trip to Paris" },
    { text: "✈️ Find Flights", query: "Find flights to Tokyo" },
    { text: "🏝 Beach Resorts", query: "Recommend beach resorts in Maldives" },
  ];

  return (
    <div className="p-4 md:p-6 bg-gradient-to-t from-white/90 via-white/80 to-transparent pt-10">
      <div className="max-w-3xl mx-auto relative">
        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-2xl shadow-[0_8px_40px_-10px_rgba(0,0,0,0.1)] border border-gray-100 p-2 flex items-center gap-2 transition-shadow focus-within:shadow-[0_12px_50px_-10px_rgba(13,148,136,0.15)] ring-4 ring-white/50">
            <button
              type="button"
              className="p-3 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded-xl transition-colors"
            >
              <Sparkles size={20} />
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={disabled}
              placeholder={
                disabled
                  ? "Travel AI is thinking..."
                  : "Tell me your travel plans..."
              }
              className="flex-1 bg-transparent border-none outline-none text-gray-700 placeholder-gray-400 text-sm h-10 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || disabled}
              className={`p-3 rounded-xl transition-all duration-300 flex items-center justify-center ${
                input.trim() && !disabled
                  ? "bg-gray-900 text-white shadow-lg shadow-gray-300 scale-100 hover:bg-gray-800"
                  : "bg-gray-100 text-gray-400 scale-95 cursor-not-allowed"
              }`}
            >
              <Send size={18} />
            </button>
          </div>
        </form>

        {/* Quick Prompts */}
        <div className="mt-4 flex gap-2 justify-start overflow-x-auto pb-2 scrollbar-hide px-1">
          {quickPrompts.map((item, i) => (
            <button
              key={i}
              onClick={() => setInput(item.query)}
              disabled={disabled}
              className="flex-shrink-0 whitespace-nowrap px-4 py-2 bg-white/40 backdrop-blur-md border border-white hover:border-teal-200 hover:bg-white text-xs font-medium text-gray-600 rounded-full transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {item.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
