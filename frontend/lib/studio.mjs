export const stageGroups = [
  {
    id: "ideas",
    title: "Ideas",
    description: "Briefs and first drafts",
    empty: "Your next idea starts here.",
    hint: "Create a project with a brief, audience and destinations.",
  },
  {
    id: "creating",
    title: "In progress",
    description: "Sources, scripts and edits",
    empty: "Space for your next creation.",
    hint: "Projects appear here as you move through their workflow.",
  },
  {
    id: "delivery",
    title: "Review & publish",
    description: "Final checks and delivery",
    empty: "Good stories take a little work.",
    hint: "Review, export and publication projects will appear here.",
  },
];

export function stageGroup(stage) {
  if (["idea", "script", "scripting"].includes(stage)) return "ideas";
  if (
    ["review", "approved", "exported", "scheduled", "published"].includes(stage)
  )
    return "delivery";
  return "creating";
}

export function workflowPosition(stage) {
  if (stage === "idea") return 0;
  if (["script", "scripting"].includes(stage)) return 1;
  if (["assets", "editing"].includes(stage)) return 2;
  if (
    ["review", "approved", "exported", "scheduled", "published"].includes(stage)
  )
    return 3;
  return 0;
}

export function nextProjectPath(projectId, stage) {
  const suffix = ["/script", "/script", "/assets", "/publish"][
    workflowPosition(stage)
  ];
  return `/projects/${projectId}${stage === "editing" ? "/clips" : suffix}`;
}

export function workflowNextAction(state) {
  if (state.stage !== "idea" || !state.checklist?.script_saved)
    return state.next_action;
  if (!state.checklist.assets_ready)
    return "Your script is saved. Add and review your source footage in Assets.";
  if (!state.checklist.editing_complete)
    return "Your script is saved. Shape your clips and finish the edit.";
  return "Your script is saved. Review your project and continue the workflow.";
}
