import { CheckSquareIcon, PlusIcon } from "@core/components/icons";
import { useLive } from "@core/live";
import type { ModuleWeb } from "@core/registry";
import { navigate } from "@core/router";
import { NavCount } from "@core/Sidebar";
import { tasksApi } from "./api";
import MyTasks from "./MyTasks";
import TaskPage from "./TaskPage";
import TasksHome from "./TasksHome";

/** The sidebar's count: your tasks that are late or due today (nothing when there are none). */
function DueCount() {
  const { data } = useLive(() => tasksApi.count("mine"));
  return <NavCount n={data ? data.late + data.due_today : undefined} />;
}

const tasks: ModuleWeb = {
  id: "tasks",
  name: "Tasks",
  nav: [{ label: "My tasks", icon: <CheckSquareIcon size={16} />, path: "tasks", badge: DueCount }],
  routes: [
    { path: "tasks", view: MyTasks },
    { path: "tasks/t/:id", view: TaskPage },
  ],
  primary: { label: "New task", icon: <PlusIcon size={16} />, run: () => navigate("tasks?new=1") },
  home: TasksHome,
};

export default tasks;
