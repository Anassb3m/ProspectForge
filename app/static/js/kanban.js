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

  // Optimistic UI move
  const originalColumnId = document.querySelector(`[data-prospect-id="${prospectId}"]`).closest('.kanban-column').id;
  const targetColumn = document.getElementById(column);
  const cardElement = document.querySelector(`[data-prospect-id="${prospectId}"]`);

  if (targetColumn && cardElement && targetColumn.id !== originalColumnId) {
      targetColumn.appendChild(cardElement);
  }

  const formData = new FormData();
  formData.append("opportunity_id", prospectId);
  formData.append("column", column);
  formData.append("channel", "Email");

  const token = typeof pfCsrf === "function" ? pfCsrf() : "";

  fetch("/kanban/move", {
    method: "POST",
    body: formData,
    headers: {
      "HX-Request": "true",
      "X-CSRF-Token": token
    },
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
      // Revert optimistic move
      if (originalColumnId && cardElement) {
         const origCol = document.getElementById(originalColumnId);
         if (origCol) origCol.appendChild(cardElement);
      }
      const board = document.getElementById("kanban-board");
      if (board) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-md mb-4";
        errorDiv.innerText = "Could not move card. Check compliance fields (data_source + informed_at for Sent).";
        board.parentElement.insertBefore(errorDiv, board);
        setTimeout(() => errorDiv.remove(), 5000);
      }
    });

  draggedProspectId = null;
}

document.addEventListener("dragend", () => {
  document.querySelectorAll(".kanban-card").forEach((el) => el.classList.remove("opacity-50"));
});
