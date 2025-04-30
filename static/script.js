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
let inputOj, inputCode, inputRating, inputProblemLink, inputTitle, inputTags, inputCustom; // Add inputCustom variable

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
  inputTitle = document.getElementById('input-title'); // Assign title input
  inputTags = document.getElementById('input-tags'); // Assign tags input
  inputCustom = document.getElementById('input-custom'); // Assign custom input

  // Verify elements are found (update check)
  if (!tbody || !modal || !modalTitle || !btnSubmit || /* btnAdd might be null */ !btnCancel || !ojFilterBtn || !ojFilterDropdown || !filterTags || !filterMode || !inputOj || !inputCode || !inputRating || !inputProblemLink || !inputTitle || !inputTags || !inputCustom) { // Add inputCustom check
      console.error("Error: One or more essential DOM elements not found!");
      // Don't return immediately if btnAdd is the only missing one (public view)
      if (!btnAdd && document.body.classList.contains('public-view')) {
          console.log("Note: Add button not found, likely public view.");
      } else if (!tbody || !modal || !modalTitle || !btnSubmit || !btnCancel || !ojFilterBtn || !ojFilterDropdown || !filterTags || !filterMode || !inputOj || !inputCode || !inputRating || !inputProblemLink || !inputTitle || !inputTags || !inputCustom) { // Add inputCustom check
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

  // Add listeners to modal OJ and Code inputs for fetching Luogu data AND Title
  inputOj.addEventListener('change', handleOjOrCodeChange); // Use a combined handler
  inputCode.addEventListener('blur', handleOjOrCodeChange); // Use a combined handler

  // Add listener for the Problem Link input
  if (inputProblemLink) {
      inputProblemLink.addEventListener('input', parseAndFillFromUrl); // Use 'input' for paste/type
  }

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

// Combined handler for OJ/Code changes to fetch Rating and Title from Luogu
async function handleOjOrCodeChange() {
    const oj = inputOj.value;
    const code = inputCode.value.trim();

    // Fetch Rating & Title from Luogu
    await maybeFetchLuoguData(oj, code); // Pass oj and code
}

// Function to attempt fetching details (Rating, Title, Tags, Custom)
async function maybeFetchLuoguData(oj, code) {
    // Add Luogu to supported OJs for fetching
    const supportedOJs = ["SPOJ", "Codeforces", "AtCoder", "UVA", "Luogu"];

    console.log(`[maybeFetchLuoguData] Triggered. OJ: "${oj}", Code: "${code}"`);

    const shouldFetch = supportedOJs.includes(oj) && code;
    console.log(`[maybeFetchLuoguData] Conditions check: supportedOJ=${supportedOJs.includes(oj)}, hasCode=${!!code}. Should Fetch: ${shouldFetch}`);

    if (shouldFetch) {
        console.log(`[maybeFetchLuoguData] Attempting to fetch details for ${oj} - ${code}`);
        // Set placeholders
        inputRating.placeholder = "Fetching Rating...";
        const fetchTitle = !inputTitle.value.trim();
        if (fetchTitle) inputTitle.placeholder = "Fetching Title...";
        // Set tags placeholder if field is empty
        const fetchTags = !inputTags.value.trim();
        if (fetchTags) inputTags.placeholder = "Fetching Tags...";
        // Only set custom placeholder if OJ is AtCoder
        const fetchCustom = oj === 'AtCoder' && !inputCustom.value.trim();
        if (fetchCustom) inputCustom.placeholder = "Fetching Custom...";
        // Luogu doesn't have a separate 'custom' field to fetch

        // Clear existing values that might be fetched
        inputRating.value = '';
        // Don't clear title/tags/custom here, clear based on fetch intent below

        try {
            const response = await fetch(`/fetch-luogu-details?oj=${encodeURIComponent(oj)}&code=${encodeURIComponent(code)}`);
            if (!response.ok) {
                console.error(`[maybeFetchLuoguData] Error fetching details from backend: ${response.status}`);
                inputRating.placeholder = "Rating Fetch failed";
                if (fetchTitle) inputTitle.placeholder = "Title Fetch failed";
                if (fetchTags) inputTags.placeholder = "Tags Fetch failed"; // Show failure if intended to fetch
                if (fetchCustom) inputCustom.placeholder = "Custom Fetch failed";
                return;
            }
            const data = await response.json();

            // Handle Rating (Always try to populate)
            if (data.rating !== null) {
                console.log(`[maybeFetchLuoguData] Received Rating: ${data.rating}`);
                inputRating.value = data.rating;
            } else {
                console.log("[maybeFetchLuoguData] Rating not found.");
            }
            inputRating.placeholder = "";

            // Handle Title
            if (fetchTitle) {
                if (data.title) {
                    console.log(`[maybeFetchLuoguData] Received Title: ${data.title}`);
                    inputTitle.value = data.title;
                } else {
                    console.log("[maybeFetchLuoguData] Title not found.");
                }
                inputTitle.placeholder = "";
            } else {
                 console.log("[maybeFetchLuoguData] Title fetch skipped as field was not empty.");
            }

            // Handle Tags (for ANY OJ if available and field was empty)
            if (fetchTags) {
                if (data.tags && Array.isArray(data.tags) && data.tags.length > 0) {
                    console.log(`[maybeFetchLuoguData] Received Tags for ${oj}: ${data.tags}`);
                    inputTags.value = data.tags.join(', ');
                } else {
                    console.log(`[maybeFetchLuoguData] Tags not found or empty for ${oj}.`);
                }
                inputTags.placeholder = ""; // Clear placeholder regardless
            } else {
                 console.log(`[maybeFetchLuoguData] Tags fetch skipped for ${oj} as field was not empty.`);
                 if (inputTags.placeholder.startsWith("Fetching")) inputTags.placeholder = ""; // Clear placeholder if fetch skipped
            }

            // Handle Custom field (ONLY for AtCoder)
            if (fetchCustom) { // fetchCustom is true only if oj === 'AtCoder' and field was empty
                if (data.custom !== null && data.custom !== undefined) {
                    console.log(`[maybeFetchLuoguData] Received AC Custom data (Score): ${data.custom}`);
                    inputCustom.value = data.custom;
                } else {
                    console.log("[maybeFetchLuoguData] AC Custom data (Score) not found.");
                }
                inputCustom.placeholder = ""; // Clear placeholder regardless
            } else if (oj === 'AtCoder') {
                 console.log("[maybeFetchLuoguData] AC Custom fetch skipped as field was not empty.");
                 if (inputCustom.placeholder.startsWith("Fetching")) inputCustom.placeholder = ""; // Clear placeholder if fetch skipped
            } else {
                 // For non-AC OJs (including Luogu), ensure custom field is clear if we didn't intend to fetch
                 if (!inputCustom.value) inputCustom.placeholder = ""; // Clear placeholder if empty
            }

        } catch (error) {
            console.error("[maybeFetchLuoguData] Error calling fetch-luogu-details endpoint:", error);
            inputRating.placeholder = "Rating Fetch error";
            if (fetchTitle) inputTitle.placeholder = "Title Fetch error";
            if (fetchTags) inputTags.placeholder = "Tags Fetch error"; // Show error if intended to fetch
            if (fetchCustom) inputCustom.placeholder = "Custom Fetch error"; // Only show custom error for AtCoder
        }
    } else {
         console.log("[maybeFetchLuoguData] Conditions not met, fetch skipped.");
         // Clear placeholders if conditions aren't met
         if (inputRating.placeholder.startsWith("Fetching")) inputRating.placeholder = "";
         if (inputTitle.placeholder.startsWith("Fetching")) inputTitle.placeholder = "";
         if (inputTags.placeholder.startsWith("Fetching")) inputTags.placeholder = "";
         if (inputCustom.placeholder.startsWith("Fetching")) inputCustom.placeholder = "";
    }
}

// Function to parse URL and fill OJ/Code fields - NOW ASYNC
async function parseAndFillFromUrl() {
    const url = inputProblemLink.value.trim();
    if (!url) return;

    console.log(`Parsing URL: ${url}`);
    let extractedOj = null;
    let extractedCode = null;
    let extractedTitle = null; // Title from UVA fetch (fallback)
    let ojChanged = false;
    let codeChanged = false;
    let titleChanged = false; // Track if title changed (specifically from UVA fetch)
    // No need for tagsChanged/customChanged here, clearing happens before fetch

    try {
        // Codeforces:
        let cfMatch = url.match(/codeforces\.com\/(?:problemset\/problem\/(\d+)\/([A-Z]\d*)|contest\/(\d+)\/problem\/([A-Z]\d*))/i);
        if (cfMatch) {
            const contestId = cfMatch[1] || cfMatch[3];
            const problemIndex = cfMatch[2] || cfMatch[4];
            if (contestId && problemIndex) {
                extractedOj = "Codeforces";
                extractedCode = contestId + problemIndex.toUpperCase();
                console.log(`Matched Codeforces: OJ=${extractedOj}, Code=${extractedCode}`);
            }
        }

        // AtCoder:
        if (!extractedCode) {
            let acMatch = url.match(/atcoder\.jp\/contests\/([a-z0-9_-]+)\/tasks\/([a-z0-9_]+)/i);
            if (acMatch && acMatch[2]) {
                extractedOj = "AtCoder";
                extractedCode = acMatch[2];
                console.log(`Matched AtCoder: OJ=${extractedOj}, Code=${extractedCode}`);
            }
        }

        // Luogu: (Add before UVA)
        if (!extractedCode) {
            let luoguMatch = url.match(/luogu\.com\.cn\/problem\/([A-Z0-9_a-z]+)/i);
            if (luoguMatch && luoguMatch[1]) {
                extractedOj = "Luogu";
                extractedCode = luoguMatch[1];
                console.log(`Matched Luogu: OJ=${extractedOj}, Code=${extractedCode}`);
            }
        }

        // UVA: Fetch ID and Title (fallback) from backend
        if (!extractedCode) {
            let uvaMatch = url.match(/onlinejudge\.org/i);
            if (uvaMatch) {
                console.log("Detected UVA URL, fetching ID & Title (fallback) from backend...");
                extractedOj = "UVA";
                inputCode.placeholder = "Fetching UVA ID...";
                inputTitle.placeholder = "Fetching Title...";
                // No placeholders for tags/custom for UVA
                inputCode.value = "";
                inputTitle.value = "";
                inputTags.value = ""; // Clear tags field
                inputCustom.value = ""; // Clear custom field
                try {
                    const response = await fetch(`/fetch-uva-id?url=${encodeURIComponent(url)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.uva_id) {
                            extractedCode = data.uva_id;
                            console.log(`Received UVA ID from backend: ${extractedCode}`);
                        } else {
                            console.warn("Backend could not extract UVA ID from page.");
                        }
                        // Store title from UVA fetch as a potential fallback
                        if (data.title) {
                            extractedTitle = data.title;
                            console.log(`Received UVA Title (fallback) from backend: ${extractedTitle}`);
                        } else {
                             console.warn("Backend could not extract UVA Title from page.");
                        }
                    } else {
                        console.error(`Backend fetch for UVA ID/Title failed: ${response.status}`);
                        const errorData = await response.json().catch(() => ({}));
                        alert(`Failed to fetch UVA ID/Title from backend: ${errorData.error || response.statusText}`);
                    }
                } catch (error) {
                    console.error("Error calling /fetch-uva-id endpoint:", error);
                    alert(`Network error fetching UVA ID/Title: ${error}`);
                } finally {
                    inputCode.placeholder = "";
                    // Don't clear title placeholder yet
                }
            }
        }

        // If OJ and Code were determined
        if (extractedOj && extractedCode) {
            const ojOptionExists = Array.from(inputOj.options).some(option => option.value === extractedOj);

            if (ojOptionExists) {
                console.log(`Updating form: OJ=${extractedOj}, Code=${extractedCode}`);
                if (inputOj.value !== extractedOj) {
                    inputOj.value = extractedOj;
                    ojChanged = true;
                }
                if (inputCode.value !== extractedCode) {
                    inputCode.value = extractedCode;
                    codeChanged = true;
                }
                // Set title from UVA fetch *only if* it exists (as fallback)
                if (extractedTitle && !inputTitle.value) {
                    inputTitle.value = extractedTitle;
                    titleChanged = true;
                    console.log(`Setting Title from UVA fetch (fallback): ${extractedTitle}`);
                }

                // --- Trigger Combined fetch AFTER updating values ---
                if (ojChanged || codeChanged || titleChanged) {
                    console.log("OJ, Code, or Title(fallback) changed, triggering combined fetch...");
                    // Clear fields *before* fetch, respecting OJ rules
                    if (!titleChanged) inputTitle.value = ''; // Clear title if not set by UVA
                    // Always clear tags and custom before fetch, maybeFetchLuoguData will populate if applicable
                    inputTags.value = '';
                    inputCustom.value = '';
                    await handleOjOrCodeChange(); // Calls maybeFetchLuoguData
                } else {
                     console.log("OJ, Code, and Title values did not change.");
                }
            } else {
                console.warn(`Extracted OJ "${extractedOj}" is not a valid option in the dropdown.`);
            }
        } else if (url && extractedOj !== "UVA") {
            console.log("URL did not match known patterns or UVA ID/Title fetch failed.");
        }

    } catch (error) {
        console.error("Error during URL parsing or subsequent fetches:", error);
        // Reset placeholders
        if (inputCode.placeholder === "Fetching UVA ID...") inputCode.placeholder = "";
        if (inputRating.placeholder.startsWith("Fetching")) inputRating.placeholder = "";
        if (inputTitle.placeholder.startsWith("Fetching")) inputTitle.placeholder = "";
        if (inputTags.placeholder.startsWith("Fetching")) inputTags.placeholder = "";
        if (inputCustom.placeholder.startsWith("Fetching")) inputCustom.placeholder = "";
    }
}

// Submit handler function
async function handleSubmit() {
    console.log("Submit (Save/Update) button clicked");
    const oj = document.getElementById('input-oj').value;
    const code = document.getElementById('input-code').value.trim();
    const title = document.getElementById('input-title').value.trim();
    const ratingInput = document.getElementById('input-rating').value;
    const custom = document.getElementById('input-custom').value.trim(); // Use inputCustom element
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

  // Get filter tags, convert to lowercase, trim, and remove empty ones
  const tagsFilter = filterTags.value.toLowerCase().split(',').map(t => t.trim()).filter(t => t);
  const mode = filterMode.value;

  // Filter logic using selectedOJs
  const indexed = tasks.map((task, i) => ({ task, i }));
  let filtered = indexed.filter(({ task }) => {
    // OJ matching logic (remains the same)
    const matchOJ = selectedOJs.length === 0 || selectedOJs.includes(task.oj);

    // --- Refined Tag Filtering Logic ---
    // Join the task's tags into a single lowercase string for searching. Handle case where tags might be null/undefined.
    const taskTagsString = task.tags ? task.tags.join(', ').toLowerCase() : '';
    let matchTags = true; // Assume match if no filter tags are entered

    if (tagsFilter.length > 0) { // Only apply tag filter if there are filter terms
        if (mode === 'or') {
            // OR mode: Check if *any* filter tag is included (partially) in the task's tags string
            matchTags = tagsFilter.some(filterTag => taskTagsString.includes(filterTag));
        } else { // mode === 'and'
            // AND mode: Check if *all* filter tags are included (partially) in the task's tags string
            matchTags = tagsFilter.every(filterTag => taskTagsString.includes(filterTag));
        }
    }
    // --- End Refined Tag Filtering Logic ---

    return matchOJ && matchTags; // Return true only if both OJ and Tag conditions are met
  });

  // Sorting logic (remains the same)
  if (sortKey) {
    filtered.sort((a, b) => {
      let va = a.task[sortKey]; let vb = b.task[sortKey];
      // Attempt numeric conversion for sorting if possible
      const numA = parseFloat(va);
      const numB = parseFloat(vb);
      if (!isNaN(numA) && !isNaN(numB)) {
          va = numA;
          vb = numB;
      } else { // Fallback to string comparison if not numeric
          va = String(va).toLowerCase();
          vb = String(vb).toLowerCase();
      }
      return va < vb ? (sortAsc ? -1 : 1) : va > vb ? (sortAsc ? 1 : -1) : 0;
    });
  }

  tbody.innerHTML = ''; // Clear existing rows

  if (filtered.length === 0) {
    // Add a visible message when no problems are found
    const tr = document.createElement('tr');
    // Adjust colspan based on the actual number of columns in your table header
    tr.innerHTML = '<td colspan="8" style="text-align: center; padding: 20px;">No problems match the current filters.</td>';
    tbody.appendChild(tr);
    return;
  }

  // Table row generation (remains the same)
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
    // Reset all fields when adding a new task
    document.getElementById('input-oj').value = "";
    document.getElementById('input-code').value = '';
    document.getElementById('input-title').value = '';
    document.getElementById('input-rating').value = '';
    document.getElementById('input-custom').value = ''; // Reset custom
    document.getElementById('input-tags').value = ''; // Reset tags
    document.getElementById('input-problem-link').value = '';
    document.getElementById('input-contest').value = 'No';
    // Clear placeholders
    document.getElementById('input-rating').placeholder = '';
    document.getElementById('input-title').placeholder = '';
    document.getElementById('input-tags').placeholder = 'tag1, tag2'; // Default placeholder
    document.getElementById('input-custom').placeholder = ''; // Default placeholder
  }
  // When editing, fields are populated by onEdit, placeholders aren't relevant
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
  document.getElementById('input-custom').value = task.custom || ''; // Populate custom field
  document.getElementById('input-tags').value = task.tags ? task.tags.join(', ') : ''; // Populate tags
  document.getElementById('input-problem-link').value = task.problem_link || ''; // Populate problem link
  document.getElementById('input-contest').value = task.contest || 'No';
  // Clear any lingering placeholders from previous operations
  document.getElementById('input-rating').placeholder = '';
  document.getElementById('input-title').placeholder = '';
  document.getElementById('input-tags').placeholder = 'tag1, tag2';
  document.getElementById('input-custom').placeholder = '';
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
