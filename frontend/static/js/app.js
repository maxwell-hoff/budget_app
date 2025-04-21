// Global variables
let currentAge = 0;
let milestones = [];

// Initialize the application
$(document).ready(function() {
    initializeEventListeners();
    loadProfile();
    loadMilestones();  // Load milestones regardless of profile status
});

// Event Listeners
function initializeEventListeners() {
    // User profile form
    $('#userProfileForm').on('submit', handleProfileSubmit);
    $('#birthday').on('change', calculateAge);
    
    // Milestone controls
    $('#addMilestone').on('click', addNewMilestone);
    
    // Bank statement upload
    $('#statementUploadForm').on('submit', handleStatementUpload);
}

// User Profile Functions
function loadProfile() {
    $.ajax({
        url: '/api/profile',
        method: 'GET',
        success: function(response) {
            if (response.birthday) {
                // Hide the profile form and show the profile info
                $('#profileForm').hide();
                $('#profileInfo').show();
                
                // Set the birthday and current age display
                const birthday = new Date(response.birthday);
                const formattedDate = birthday.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
                $('#savedBirthday').text(formattedDate);
                $('#savedCurrentAge').text(currentAge);
                
                // Set the birthday input value and calculate age
                $('#birthday').val(response.birthday);
                calculateAge();
                
                // Update the timeline with the loaded birthday
                window.timeline.updateTimeline();
                
                loadMilestones();
            } else {
                // Show the profile form if no birthday is saved
                $('#profileForm').show();
                $('#profileInfo').hide();
            }
        },
        error: function(error) {
            console.error('Error loading profile:', error);
            // Show the profile form if there's an error
            $('#profileForm').show();
            $('#profileInfo').hide();
        }
    });
}

function calculateAge() {
    const birthday = new Date($('#birthday').val());
    const today = new Date();
    const age = today.getFullYear() - birthday.getFullYear();
    const monthDiff = today.getMonth() - birthday.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthday.getDate())) {
        currentAge = age - 1;
    } else {
        currentAge = age;
    }
    
    $('#currentAge').val(currentAge);
    $('#savedCurrentAge').text(currentAge);
}

function handleProfileSubmit(e) {
    e.preventDefault();
    const birthday = $('#birthday').val();
    
    // Save profile and create default milestones
    $.ajax({
        url: '/api/profile',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ birthday: birthday }),
        success: function(response) {
            // After saving profile, create default milestones
            createDefaultMilestones();
            loadMilestones();
        },
        error: function(error) {
            console.error('Error saving profile:', error);
            alert('Error saving profile. Please try again.');
        }
    });
}

// Milestone Functions
function createDefaultMilestones() {
    // Create Current milestone
    $.ajax({
        url: '/api/milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: 'Current',
            age_at_occurrence: currentAge,
            expense_type: 'lump_sum',
            amount: 0
        }),
        success: function(response) {
            console.log('Created Current milestone');
        },
        error: function(error) {
            console.error('Error creating Current milestone:', error);
        }
    });

    // Create Inheritance milestone
    $.ajax({
        url: '/api/milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: 'Inheritance',
            age_at_occurrence: 100,
            expense_type: 'lump_sum',
            amount: 10000
        }),
        success: function(response) {
            console.log('Created Inheritance milestone');
        },
        error: function(error) {
            console.error('Error creating Inheritance milestone:', error);
        }
    });
}

function loadMilestones() {
    $.ajax({
        url: '/api/milestones',
        method: 'GET',
        success: function(response) {
            milestones = response;
            updateTimeline();
            response.forEach(createMilestoneForm);
        },
        error: function(error) {
            console.error('Error loading milestones:', error);
            alert('Error loading milestones. Please try again.');
        }
    });
}

function addNewMilestone() {
    const milestone = {
        name: 'New Milestone',
        age_at_occurrence: currentAge + 5,
        expense_type: 'lump_sum',
        amount: 0
    };
    
    $.ajax({
        url: '/api/milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(milestone),
        success: function(response) {
            milestones.push(response);
            updateTimeline();
            createMilestoneForm(response);
        },
        error: function(error) {
            console.error('Error creating milestone:', error);
            alert('Error creating milestone. Please try again.');
        }
    });
}

function updateTimeline() {
    // Clear existing milestones
    $('#timeline-milestones').empty();
    
    // Add each milestone to the timeline
    milestones.forEach(milestone => {
        window.timeline.addMilestone(milestone);
    });
}

function createMilestoneForm(milestone) {
    const form = $(`
        <div class="milestone-form" data-id="${milestone.id}">
            <h3>${milestone.name}</h3>
            <form class="milestone-form-content">
                <div class="mb-3">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control" name="name" value="${milestone.name}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Age at Occurrence</label>
                    <input type="number" class="form-control" name="age_at_occurrence" value="${milestone.age_at_occurrence}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Expense Type</label>
                    <select class="form-control" name="expense_type">
                        <option value="lump_sum" ${milestone.expense_type === 'lump_sum' ? 'selected' : ''}>Lump Sum</option>
                        <option value="annuity" ${milestone.expense_type === 'annuity' ? 'selected' : ''}>Annuity</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Amount</label>
                    <input type="number" class="form-control" name="amount" value="${milestone.amount}">
                </div>
                <button type="submit" class="btn btn-primary">Save</button>
                <button type="button" class="btn btn-danger delete-milestone">Delete</button>
            </form>
        </div>
    `);
    
    $('#milestoneForms').append(form);
    
    // Add event listeners for the new form
    form.find('.milestone-form-content').on('submit', handleMilestoneUpdate);
    form.find('.delete-milestone').on('click', handleMilestoneDelete);
}

function handleMilestoneUpdate(e) {
    e.preventDefault();
    const form = $(e.target);
    const milestoneId = form.closest('.milestone-form').data('id');
    const milestone = milestones.find(m => m.id === milestoneId);
    
    if (milestone) {
        const updatedMilestone = {
            name: form.find('[name="name"]').val(),
            age_at_occurrence: parseInt(form.find('[name="age_at_occurrence"]').val()),
            expense_type: form.find('[name="expense_type"]').val(),
            amount: parseFloat(form.find('[name="amount"]').val())
        };
        
        $.ajax({
            url: `/api/milestones/${milestoneId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(updatedMilestone),
            success: function(response) {
                Object.assign(milestone, response);
                updateTimeline();
            },
            error: function(error) {
                console.error('Error updating milestone:', error);
                alert('Error updating milestone. Please try again.');
            }
        });
    }
}

function handleMilestoneDelete(e) {
    const form = $(e.target).closest('.milestone-form');
    const milestoneId = form.data('id');
    
    $.ajax({
        url: `/api/milestones/${milestoneId}`,
        method: 'DELETE',
        success: function() {
            milestones = milestones.filter(m => m.id !== milestoneId);
            form.remove();
            updateTimeline();
        },
        error: function(error) {
            console.error('Error deleting milestone:', error);
            alert('Error deleting milestone. Please try again.');
        }
    });
}

// Bank Statement Functions
function handleStatementUpload(e) {
    e.preventDefault();
    const file = $('#statementFile')[0].files[0];
    
    if (file) {
        const formData = new FormData();
        formData.append('file', file);
        
        $.ajax({
            url: '/api/parse-statement',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: displayBalanceSheet,
            error: handleError
        });
    }
}

function displayBalanceSheet(data) {
    const balanceSheet = $('#balanceSheet');
    balanceSheet.empty();
    
    balanceSheet.append(`
        <div class="balance-sheet-item">
            <h4>Total Income: $${data.total_income.toFixed(2)}</h4>
        </div>
    `);
    
    for (const [category, amount] of Object.entries(data.expenses_by_category)) {
        balanceSheet.append(`
            <div class="balance-sheet-item">
                <strong>${category}:</strong> $${Math.abs(amount).toFixed(2)}
            </div>
        `);
    }
    
    balanceSheet.append(`
        <div class="balance-sheet-item">
            <h4>Net Worth: $${data.net_worth.toFixed(2)}</h4>
        </div>
    `);
}

// Utility Functions
function handleError(error) {
    console.error('Error:', error);
    alert('An error occurred. Please try again.');
} 