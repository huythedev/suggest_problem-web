// --- Function to load problems ---
async function loadProblems() {
    try {
        const response = await fetch('/problems');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const problems = await response.json();
        const tbody = document.getElementById('problems-tbody');
        tbody.innerHTML = ''; // Clear existing rows
        problems.forEach(problem => {
            const row = tbody.insertRow();
            // Ensure the order matches the <thead>
            row.innerHTML = `
                <td>${escapeHtml(problem.oj)}</td>
                <td>${escapeHtml(problem.code)}</td>
                <td>${escapeHtml(problem.title)}</td>
                <td>${escapeHtml(problem.rating)}</td>
                <td>${escapeHtml(problem.contest || 'No')}</td> <!-- Contest data in 5th cell -->
                <!-- Add other cells like Tags, Custom here if they exist -->
                <td> <!-- Actions buttons in the LAST cell -->
                    <button class="edit-btn" onclick="editProblem(
                        '${escapeHtml(problem.oj)}',
                        '${escapeHtml(problem.code)}',
                        '${escapeHtml(problem.title)}',
                        '${escapeHtml(problem.rating)}',
                        '${escapeHtml(problem.contest || 'No')}'
                        // Add other fields like tags, custom here if needed for editing
                    )">Edit</button>
                    <button class="delete-btn" onclick="deleteProblem('${escapeHtml(problem.oj)}', '${escapeHtml(problem.code)}')">Delete</button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Error loading problems:', error);
        // Optionally display an error message to the user
        const tbody = document.getElementById('problems-tbody');
        tbody.innerHTML = '<tr><td colspan="6">Error loading problems. Please try again later.</td></tr>'; // Adjust colspan if needed
    }
}

// --- Function to populate edit form ---
// Ensure the function signature matches the parameters passed in the onclick handler
function editProblem(oj, code, title, rating, contest /*, other fields */) {
    // ... (rest of the function remains the same as previous suggestion)
    document.getElementById('oj').value = oj;
    document.getElementById('code').value = code;
    document.getElementById('title').value = title;
    document.getElementById('rating').value = rating;
    document.getElementById('contest').value = contest; // Populate contest field
    // Populate other fields if they exist
    document.getElementById('add-problem-btn').style.display = 'none';
    document.getElementById('update-problem-btn').style.display = 'inline-block';
    document.getElementById('cancel-update-btn').style.display = 'inline-block';
    // Store original identifiers for the update request
    document.getElementById('update-problem-btn').dataset.originalOj = oj;
    document.getElementById('update-problem-btn').dataset.originalCode = code;
}

// ... (addProblem, updateProblem, escapeHtml functions remain the same) ...

// --- Initial load ---
document.addEventListener('DOMContentLoaded', loadProblems); // Make sure this runs
