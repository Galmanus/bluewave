import { useState, useMemo } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Send } from "lucide-react";
import { useCalendar, usePublishPost } from "../hooks/useCalendar";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const start = new Date(year, month, 1).toISOString();
  const end = new Date(year, month + 1, 0, 23, 59, 59).toISOString();

  const { data: posts = [], isLoading } = useCalendar(start, end);
  const publishPost = usePublishPost();

  const postsByDay = useMemo(() => {
    const map: Record<number, typeof posts> = {};
    posts.forEach(p => {
      const day = new Date(p.scheduled_at).getDate();
      if (!map[day]) map[day] = [];
      map[day].push(p);
    });
    return map;
  }, [posts]);

  const firstDayOfWeek = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = Array.from({ length: 42 }, (_, i) => {
    const day = i - firstDayOfWeek + 1;
    return day > 0 && day <= daysInMonth ? day : null;
  });

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  const monthLabel = currentDate.toLocaleString("default", { month: "long", year: "numeric" });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CalendarDays className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold">Content Calendar</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-lg font-medium min-w-[160px] text-center">{monthLabel}</span>
          <button onClick={nextMonth} className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-500">Loading calendar...</div>
      ) : (
        <div className="border rounded-lg overflow-hidden dark:border-gray-700">
          <div className="grid grid-cols-7 bg-gray-50 dark:bg-gray-800">
            {DAY_NAMES.map(d => (
              <div key={d} className="p-2 text-center text-sm font-medium text-gray-500">{d}</div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((day, i) => (
              <div
                key={i}
                className={`min-h-[100px] border-t border-r dark:border-gray-700 p-1 ${
                  day ? "bg-white dark:bg-gray-900" : "bg-gray-50 dark:bg-gray-800/50"
                }`}
              >
                {day && (
                  <>
                    <div className="text-xs text-gray-400 mb-1">{day}</div>
                    {(postsByDay[day] || []).slice(0, 3).map(p => (
                      <div
                        key={p.id}
                        className={`text-xs px-1 py-0.5 rounded mb-0.5 truncate ${
                          p.status === "published" ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" :
                          p.status === "failed" ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" :
                          p.status === "cancelled" ? "bg-gray-100 text-gray-500" :
                          "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                        }`}
                        title={`${p.channel} — ${p.status}`}
                      >
                        <span className="font-medium">{p.channel}</span>
                        {p.status === "scheduled" && (
                          <button
                            onClick={() => publishPost.mutate(p.id)}
                            className="ml-1 text-blue-600 hover:underline"
                            title="Publish now"
                          >
                            <Send className="w-3 h-3 inline" />
                          </button>
                        )}
                      </div>
                    ))}
                    {(postsByDay[day]?.length || 0) > 3 && (
                      <div className="text-xs text-gray-400">+{postsByDay[day].length - 3} more</div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {posts.length === 0 && !isLoading && (
        <p className="text-center text-gray-500 py-4">
          No posts scheduled for {monthLabel}. Approve assets and schedule them here.
        </p>
      )}
    </div>
  );
}
