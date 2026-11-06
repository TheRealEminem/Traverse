// Home's card: what's next for you. What's due this week, late first; with nothing due, what you're doing, then what's
// open, so the card always says where to go next.
import { CheckSquareIcon } from "@core/components/icons";
import { useLive } from "@core/live";
import { tasksApi } from "./api";
import { addDays, todayIso } from "./dates";
import { TaskList } from "./TaskRow";

export default function TasksHome() {
  const { data: tasks, reload } = useLive(() => tasksApi.list({ assignee: "mine", status: "todo,doing" }));
  const { data: meta } = useLive(tasksApi.meta);
  const weekEnd = addDays(todayIso(), 7);
  const soon = (tasks ?? []).filter((t) => t.due_on && t.due_on <= weekEnd);
  const next = soon.length ? soon : [...(tasks ?? [])].sort((a, b) => Number(b.status === "doing") - Number(a.status === "doing"));
  return (
    <>
      <div className="flex items-center gap-3">
        <span className="well well-forest">
          <CheckSquareIcon size={16} />
        </span>
        <div className="min-w-0">
          <h2 className="text-heading font-semibold tracking-[-0.01em]">What's next</h2>
          <p className="text-hint text-ink-soft">
            {tasks
              ? soon.length
                ? `${soon.length} due this week`
                : tasks.length
                  ? `Nothing due this week · ${tasks.filter((t) => t.status === "doing").length ? "what you're doing" : "what's open"}`
                  : "All done"
              : "…"}
          </p>
        </div>
      </div>
      {next.length > 0 && (
        <div className="-mx-5 mt-3 [&_.panel]:rounded-none [&_.panel]:border-x-0 [&_.panel]:shadow-none">
          <TaskList tasks={next.slice(0, 5)} meta={meta ?? null} onChanged={() => void reload()} label="What's next" />
        </div>
      )}
      <a href={soon.length ? "#/tasks?when=week" : "#/tasks"} className="btn btn-sm btn-ghost -ml-3 mt-2">
        See all
      </a>
    </>
  );
}
