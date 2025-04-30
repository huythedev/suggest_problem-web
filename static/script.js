// Data storage
let tasks = [];
let sortKey = null;
let sortAsc = true;
let editingIndex = null;

// DOM elements (Declare globally or pass as needed)
let tbody, modal, modalTitle, btnSubmit, btnAdd, btnCancel, filterTags, filterMode, tableHeaders;
// Custom OJ Filter elements
let ojFilterBtn, ojFilterDropdown, ojFilterCheckboxes;
// Modal input elements for fetching and link
let inputOj, inputCode, inputRating, inputProblemLink;

// Load data from backend
async function loadData() {
  try {
    const res = await fetch('/problems');
    tasks = await res.json();
  } catch (err) {
    console.error('Error loading from backend', err);
    tasks = [];
  }
}

// Save to backend (Add Task - POST)
async function saveTaskToBackend(task) {
  const res = await fetch('/problems', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task)
  });

  if (!res.ok) {
    let errorMsg = `Failed to save task. Status: ${res.status}`;
    try {
      const errorData = await res.json();
      if (errorData && errorData.error) {
        errorMsg = errorData.error;
      }
    } catch (e) {
      console.warn("Could not parse error response body:", e);
    }
    throw new Error(errorMsg);
  }
}

// Initialize on load
window.addEventListener('DOMContentLoaded', async () => {
  console.log("DOM fully loaded and parsed");

  // Assign DOM elements once
  tbody = document.querySelector('#task-table tbody');
  modal = document.getElementById('modal');
  modalTitle = document.getElementById('modal-title');
  btnSubmit = document.getElementById('btn-submit');
  btnAdd = document.getElementById('btn-add');
  btnCancel = document.getElementById('btn-cancel');
  // OJ Filter elements
  ojFilterBtn = document.getElementById('oj-filter-btn');
  ojFilterDropdown = document.getElementById('oj-filter-dropdown');
  ojFilterCheckboxes = document.querySelectorAll('.oj-filter-checkbox');
  // Other filters
  filterTags = document.getElementById('filter-tags');
  filterMode = document.getElementById('filter-mode');
  tableHeaders = document.querySelectorAll('th[data-key]');
  // Modal inputs needed for fetch and link
  inputOj = document.getElementById('input-oj');
  inputCode = document.getElementById('input-code');
  inputRating = document.getElementById('input-rating');
  inputProblemLink = document.getElementById('input-problem-link');

  // Verify elements are found (update check)
  if (!tbody || !modal || !modalTitle || !btnSubmit || /* btnAdd might be null */ !btnCancel || !ojFilterBtn || !ojFilterDropdown || !filterTags || !filterMode || !inputOj || !inputCode || !inputRating || !inputProblemLink) {
      console.error("Error: One or more essential DOM elements not found!");
      // Don't return immediately if btnAdd is the only missing one (public view)
      if (!btnAdd && document.body.classList.contains('public-view')) {
          console.log("Note: Add button not found, likely public view.");
      } else if (!tbody || !modal || !modalTitle || !btnSubmit || !btnCancel || !ojFilterBtn || !ojFilterDropdown || !filterTags || !filterMode || !inputOj || !inputCode || !inputRating || !inputProblemLink) {
          return; // Stop if other critical elements missing
      }
  }
  console.log("Essential DOM elements found.");

  // Load initial data
  await loadData();
  renderTable(); // Initial render

  // --- Attach Event Listeners ONCE ---
  console.log("Attaching event listeners...");

  // Custom OJ Filter Logic
  ojFilterBtn.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent click from immediately closing dropdown
      ojFilterDropdown.classList.toggle('hidden');
  });

  // Add listener to checkboxes container or individual checkboxes
  ojFilterDropdown.addEventListener('change', () => {
      updateOjFilterButtonText();
      renderTable(); // Re-render table when selection changes
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
      if (!ojFilterDropdown.classList.contains('hidden') && !ojFilterBtn.contains(e.target) && !ojFilterDropdown.contains(e.target)) {
          ojFilterDropdown.classList.add('hidden');
      }
  });

  // Other Filters & Sort
  filterTags.addEventListener('input', renderTable);
  filterMode.addEventListener('change', renderTable);
  tableHeaders.forEach(th =>
    th.addEventListener('click', () => {
      console.log(`Sort header clicked: ${th.dataset.key}`);
      const key = th.dataset.key;
      if (sortKey === key) sortAsc = !sortAsc;
      else { sortKey = key; sortAsc = true; }
      renderTable();
    })
  );

  // Modal Buttons
  // Ensure btnAdd exists before adding listener (especially for public view)
  if (btnAdd) {
      btnAdd.addEventListener('click', () => {
          console.log("Add Task button clicked");
          showModal();
      });
  } else {
      console.log("Add Task button not found (expected in public view).");
  }
  btnCancel.addEventListener('click', () => {
      console.log("Cancel button clicked");
      hideModal();
  });
  btnSubmit.addEventListener('click', handleSubmit); // Use named function

  // Add listeners to modal OJ and Code inputs for fetching Luogu data
  inputOj.addEventListener('change', maybeFetchLuoguData); // Use change for select
  inputCode.addEventListener('blur', maybeFetchLuoguData); // Use blur for text input

  console.log("Event listeners attached.");
}); // End of DOMContentLoaded listener

// Function to update OJ filter button text
function updateOjFilterButtonText() {
    const selectedCount = document.querySelectorAll('.oj-filter-checkbox:checked').length;
    if (selectedCount === 0) {
        ojFilterBtn.textContent = 'Select OJ(s)';
    } else if (selectedCount === 1) {
        ojFilterBtn.textContent = document.querySelector('.oj-filter-checkbox:checked').value;
    } else {
        ojFilterBtn.textContent = `${selectedCount} OJ(s) selected`;
    }
}

// Function to attempt fetching Luogu data
async function maybeFetchLuoguData() {
    const oj = inputOj.value;
    const code = inputCode.value.trim();
    const currentRating = inputRating.value; // Get current rating value
    const supportedOJs = ["SPOJ", "Codeforces", "AtCoder", "UVA"]; // OJs supported by our backend fetcher

    console.log(`[maybeFetchLuoguData] Triggered. OJ: "${oj}", Code: "${code}", Current Rating: "${currentRating}"`);

    // Only fetch if OJ is supported, code is entered, and rating is currently empty
    const shouldFetch = supportedOJs.includes(oj) && code && !currentRating;
    console.log(`[maybeFetchLuoguData] Conditions check: supportedOJ=${supportedOJs.includes(oj)}, hasCode=${!!code}, ratingIsEmpty=${!currentRating}. Should Fetch: ${shouldFetch}`);

    if (shouldFetch) {
        console.log(`[maybeFetchLuoguData] Attempting to fetch Luogu data for ${oj} - ${code}`);
        // Optional: Show a loading indicator near the rating field
        inputRating.placeholder = "Fetching...";
        try {
            const response = await fetch(`/fetch-luogu-details?oj=${encodeURIComponent(oj)}&code=${encodeURIComponent(code)}`);
            if (!response.ok) {
                // Handle HTTP errors from our backend endpoint
                console.error(`[maybeFetchLuoguData] Error fetching details from backend: ${response.status}`);
                // Optionally show an error message to the user
                inputRating.placeholder = "Fetch failed"; // Reset placeholder
                return;
            }
            const data = await response.json();
            if (data.rating !== null) {
                console.log(`[maybeFetchLuoguData] Received Luogu rating: ${data.rating}`);
                inputRating.value = data.rating; // Set the rating input
                inputRating.placeholder = ""; // Clear placeholder
            } else {
                console.log("[maybeFetchLuoguData] Luogu rating not found or OJ not supported by backend.");
                inputRating.placeholder = ""; // Clear placeholder
            }
        } catch (error) {
            console.error("[maybeFetchLuoguData] Error calling fetch-luogu-details endpoint:", error);
            inputRating.placeholder = "Fetch error"; // Reset placeholder
        }
    } else {
         console.log("[maybeFetchLuoguData] Conditions not met, fetch skipped.");
         // Clear placeholder if conditions aren't met (e.g., user cleared code)
         if (inputRating.placeholder === "Fetching..." || inputRating.placeholder === "Fetch failed" || inputRating.placeholder === "Fetch error") {
             inputRating.placeholder = "";
         }
    }
}

// Submit handler function
async function handleSubmit() {
    console.log("Submit (Save/Update) button clicked");
    const oj = document.getElementById('input-oj').value;
    const code = document.getElementById('input-code').value.trim();
    const title = document.getElementById('input-title').value.trim();
    const ratingInput = document.getElementById('input-rating').value;
    const custom = document.getElementById('input-custom').value.trim();
    const tags = document.getElementById('input-tags').value.split(',').map(t => t.trim()).filter(t => t);
    const contest = document.getElementById('input-contest').value.trim() || 'No';
    const problemLink = document.getElementById('input-problem-link').value.trim();

    if (!oj || !code || !title || ratingInput === '') {
        alert('Please fill in all required fields (OJ, Code, Title, Rating).');
        return;
    }
    const rating = parseFloat(ratingInput);
    if (isNaN(rating)) {
        alert('Please enter a valid number for Rating.');
        return;
    }
    const task = { oj, code, title, rating, custom, tags, contest, problem_link: problemLink || null };
    console.log("Data being sent:", task); // Check if data is read correctly

    // Disable button during operation
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Saving...';

    try {
        if (editingIndex !== null) {
            // --- EDIT LOGIC ---
            const originalTask = tasks[editingIndex];
            if (!originalTask) throw new Error("Original task data not found for editing.");

            const res = await fetch(`/problems?oj=${encodeURIComponent(originalTask.oj)}&code=${encodeURIComponent(originalTask.code)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(task)
            });
            if (!res.ok) {
                let errorMsg = `Failed to update task. Status: ${res.status}`;
                try { const errorData = await res.json(); if (errorData && errorData.error) errorMsg = errorData.error; } catch (e) { /* ignore */ }
                throw new Error(errorMsg);
            }
        } else {
            // --- ADD LOGIC ---
            await saveTaskToBackend(task); // This throws on error
        }
        // Success: Reload data, re-render, hide modal
        await loadData();
        renderTable();
        hideModal();
    } catch (err) {
        // Handle errors from either ADD or EDIT
        console.error('Error submitting task:', err);
        alert(`Error: ${err.message}`); // Show specific error
    } finally {
        // Re-enable button and reset text
        btnSubmit.disabled = false;
        // Reset text based on whether modal is still open (it shouldn't be on success)
        btnSubmit.textContent = editingIndex !== null ? 'Update' : 'Save';
        // Reset editingIndex if it was an edit operation that failed but didn't hide modal
        // editingIndex = null; // Resetting here might be complex if user wants to retry edit
    }
}

// Helper function to check if a string is a URL
function isUrl(str) {
    if (typeof str !== 'string') return false;
    // Simple check for http:// or https://
    return str.startsWith('http://') || str.startsWith('https://');
}

// Render table rows
function renderTable() {
  console.log("Rendering table...");
  // Ensure tbody is available
  if (!tbody) {
      console.error("renderTable: tbody not found!");
      return;
  }

  // Get selected OJs from checkboxes
  const selectedOJs = Array.from(document.querySelectorAll('.oj-filter-checkbox:checked')).map(cb => cb.value);

  const tagsFilter = filterTags.value.toLowerCase().split(',').map(t => t.trim()).filter(t => t);
  const mode = filterMode.value;

  // Filter logic using selectedOJs
  const indexed = tasks.map((task, i) => ({ task, i }));
  let filtered = indexed.filter(({ task }) => {
    // Updated OJ matching logic
    const matchOJ = selectedOJs.length === 0 || selectedOJs.includes(task.oj);

    const tags = task.tags ? task.tags.map(t => t.toLowerCase()) : [];
    let matchTags = true;
    if (tagsFilter.length) {
      matchTags = mode === 'or' ? tagsFilter.some(f => tags.includes(f)) : tagsFilter.every(f => tags.includes(f));
    }
    return matchOJ && matchTags;
  });

  // ... Sort logic ...
  if (sortKey) {
    filtered.sort((a, b) => {
      let va = a.task[sortKey]; let vb = b.task[sortKey];
      if (!isNaN(va)) va = parseFloat(va); if (!isNaN(vb)) vb = parseFloat(vb);
      return va < vb ? (sortAsc ? -1 : 1) : va > vb ? (sortAsc ? 1 : -1) : 0;
    });
  }

  tbody.innerHTML = ''; // Clear existing rows
  filtered.forEach(({ task, i }) => {
    const tr = document.createElement('tr');

    // Generate contest cell content
    let contestContent;
    const contestValue = task.contest || 'No'; // Default to 'No' if null/empty
    if (isUrl(contestValue)) {
        // It's a URL, create a clickable link with truncation class
        contestContent = `<a href="${escapeHtml(contestValue)}" target="_blank" rel="noopener noreferrer" class="contest-link" title="${escapeHtml(contestValue)}">${escapeHtml(contestValue)}</a>`;
    } else {
        // Not a URL, just display the text
        contestContent = escapeHtml(contestValue);
    }

    // Generate code cell content (link or text)
    let codeContent;
    const codeValue = task.code;
    const problemLinkValue = task.problem_link; // Get the link from task data
    if (problemLinkValue && isUrl(problemLinkValue)) {
        // It has a valid URL, make the code cell a link
        codeContent = `<a href="${escapeHtml(problemLinkValue)}" target="_blank" rel="noopener noreferrer" class="problem-code-link" title="${escapeHtml(problemLinkValue)}">${escapeHtml(codeValue)}</a>`;
    } else {
        // No link or invalid link, just display the code text
        codeContent = escapeHtml(codeValue);
    }

    // Use original index 'i' from before filtering/sorting for data-index
    tr.innerHTML = `
      <td>${escapeHtml(task.oj)}</td>
      <td>${codeContent}</td> <!-- Use generated code content -->
      <td>${escapeHtml(task.title)}</td>
      <td>${escapeHtml(task.rating)}</td>
      <td>${escapeHtml(task.custom || '')}</td>
      <td>${escapeHtml(task.tags ? task.tags.join(', ') : '')}</td>
      <td>${contestContent}</td> <!-- Use generated contest content -->
      <td>
        <button class="edit-btn" data-index="${i}">Edit</button>
        <button class="delete-btn" data-index="${i}">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach listeners to newly created buttons within this specific table body
  console.log("Attaching edit/delete listeners within renderTable...");
  tbody.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', onEdit);
  });
  tbody.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', onDelete);
  });
  console.log("Edit/delete listeners attached.");
}

// Modal show/hide
function showModal(edit = false) {
  if (!edit) {
    document.getElementById('input-oj').value = "";
    document.getElementById('input-code').value = '';
    document.getElementById('input-title').value = '';
    document.getElementById('input-rating').value = '';
    document.getElementById('input-custom').value = '';
    document.getElementById('input-tags').value = '';
    document.getElementById('input-problem-link').value = ''; // Reset problem link field
    document.getElementById('input-contest').value = 'No';
  }
  modal.classList.remove('hidden');
  modalTitle.textContent = edit ? 'Edit Task' : 'Add Task';
  btnSubmit.textContent = edit ? 'Update' : 'Save';
}

function hideModal() {
  modal.classList.add('hidden');
  editingIndex = null;
}

// Edit handler - Ensure it uses the correct index
function onEdit(e) {
  const button = e.target;
  const index = Number(button.dataset.index); // Get index from the button clicked
  console.log("Edit button clicked for original index:", index);
  if (isNaN(index) || index < 0 || index >= tasks.length) {
      console.error("Invalid index for edit:", index);
      return;
  }
  editingIndex = index; // Store the original index
  const task = tasks[index]; // Get task using the original index
  document.getElementById('input-oj').value = task.oj;
  document.getElementById('input-code').value = task.code;
  document.getElementById('input-title').value = task.title;
  document.getElementById('input-rating').value = task.rating;
  document.getElementById('input-custom').value = task.custom || '';
  document.getElementById('input-tags').value = task.tags ? task.tags.join(', ') : '';
  document.getElementById('input-problem-link').value = task.problem_link || ''; // Populate problem link
  document.getElementById('input-contest').value = task.contest || 'No';
  showModal(true);
}

// Delete handler - Ensure it uses the correct index
async function onDelete(e) {
  const button = e.target;
  const index = Number(button.dataset.index); // Get index from the button clicked
  console.log("Delete button clicked for original index:", index);
   if (isNaN(index) || index < 0 || index >= tasks.length) {
      console.error("Invalid index for delete:", index);
      return;
  }
  const taskToDelete = tasks[index]; // Get task using the original index
  if (confirm(`Xóa bài "${taskToDelete.title}" (${taskToDelete.oj} - ${taskToDelete.code})?`)) {
    try {
      const res = await fetch(`/problems?oj=${encodeURIComponent(taskToDelete.oj)}&code=${encodeURIComponent(taskToDelete.code)}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to delete task from server');
      }
      await loadData();
      renderTable();
    } catch (err) {
      console.error('Error deleting task:', err);
      alert(`Error deleting task: ${err.message}`);
    }
  }
}

// Add escapeHtml function if not already present
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe);
     }
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
