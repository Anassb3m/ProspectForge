/**
 * Kanban drag-and-drop — posts column changes via HTMX-friendly form to /kanban/move
 */
let draggedProspectId = null;

function handleKanbanDrag(event) {
  draggedProspectId = event.currentTarget.dataset.prospectId;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", draggedProspectId);
  event.currentTarget.classList.add("opacity-50");
}

function handleKanbanDrop(event, column) {
  event.preventDefault();
  const dropZone = event.currentTarget;
  dropZone.classList.remove("ring-2", "ring-brand-400");

  const prospectId = draggedProspectId || event.dataTransfer.getData("text/plain");
  if (!prospectId) return;

  // Clear drag styling
  document.querySelectorAll(".kanban-card").forEach((el) => el.classList.remove("opacity-50"));

  const formData = new FormData();
  formData.append("prospect_id", prospectId);
  formData.append("column", column);
  formData.append("channel", "Email");

  fetch("/kanban/move", {
    method: "POST",
    body: formData,
    headers: { "HX-Request": "true" },
    credentials: "same-origin",
  })
    .then((res) => {
      if (!res.ok) return res.text().then((t) => Promise.reject(t));
      return res.text();
    })
    .then((html) => {
      const board = document.getElementById("kanban-board");
      if (board) board.innerHTML = html;
    })
    .catch((err) => {
      console.error("Kanban move failed:", err);
      alert("Could not move card. Check compliance fields (data_source + informed_at for Sent).");
    });

  draggedProspectId = null;
}

document.addEventListener("dragend", () => {
  document.querySelectorAll(".kanban-card").forEach((el) => el.classList.remove("opacity-50"));
});
