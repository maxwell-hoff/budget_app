// Global variables
let currentAge = 0;
let milestones = [];

// Initialize the application
$(document).ready(function() {
    initializeEventListeners();
    loadProfile();
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
    // Create both milestones in parallel and wait for both to complete
    Promise.all([
        // Create Current milestone
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Current',
                age_at_occurrence: currentAge,
                milestone_type: 'Expense',
                disbursement_type: 'Fixed Duration',
                amount: 0,
                occurrence: 'Yearly',
                duration: 1,
                rate_of_return: 0.0
            })
        }),
        // Create Inheritance milestone
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Inheritance',
                age_at_occurrence: 100,
                milestone_type: 'Income',
                disbursement_type: 'Fixed Duration',
                amount: 10000,
                occurrence: 'Yearly',
                duration: 1,
                rate_of_return: 0.0
            })
        })
    ])
    .then(() => {
        console.log('Created default milestones');
        loadMilestones();
    })
    .catch(error => {
        console.error('Error creating default milestones:', error);
        alert('Error creating default milestones. Please try again.');
    });
}

function loadMilestones() {
    $.ajax({
        url: '/api/milestones',
        method: 'GET',
        success: function(response) {
            milestones = response;
            updateTimeline();
            
            // Clear existing milestone forms before creating new ones
            $('#milestoneForms').empty();
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
        milestone_type: 'Expense',
        disbursement_type: 'Fixed Duration',
        amount: 0,
        payment: null,
        occurrence: 'Yearly',
        duration: 1,
        rate_of_return: 0.0
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
                    <label class="form-label">Milestone Type</label>
                    <select class="form-control" name="milestone_type">
                        <option value="Expense" ${milestone.milestone_type === 'Expense' ? 'selected' : ''}>Expense</option>
                        <option value="Income" ${milestone.milestone_type === 'Income' ? 'selected' : ''}>Income</option>
                        <option value="Asset" ${milestone.milestone_type === 'Asset' ? 'selected' : ''}>Asset</option>
                        <option value="Liability" ${milestone.milestone_type === 'Liability' ? 'selected' : ''}>Liability</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Disbursement Type</label>
                    <select class="form-control" name="disbursement_type">
                        <option value="Fixed Duration" ${milestone.disbursement_type === 'Fixed Duration' ? 'selected' : ''}>Fixed Duration</option>
                        <option value="Perpetuity" ${milestone.disbursement_type === 'Perpetuity' ? 'selected' : ''}>Perpetuity</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Amount</label>
                    <input type="number" class="form-control" name="amount" value="${milestone.amount}">
                </div>
                <div class="mb-3 payment-field" style="display: ${['Asset', 'Liability'].includes(milestone.milestone_type) ? 'block' : 'none'}">
                    <label class="form-label">Payment (enter negative value for asset withdrawals / enter positive value for liability payments)</label>
                    <input type="number" class="form-control" name="payment" value="${milestone.payment || ''}">
                </div>
                <div class="mb-3 annuity-fields" style="display: ${milestone.disbursement_type ? 'block' : 'none'}">
                    <label class="form-label">Occurrence</label>
                    <select class="form-control" name="occurrence">
                        <option value="Monthly" ${milestone.occurrence === 'Monthly' ? 'selected' : ''}>Monthly</option>
                        <option value="Yearly" ${milestone.occurrence === 'Yearly' ? 'selected' : ''}>Yearly</option>
                    </select>
                </div>
                <div class="mb-3 annuity-fields duration-field" style="display: ${milestone.disbursement_type === 'Fixed Duration' ? 'block' : 'none'}">
                    <label class="form-label">Duration</label>
                    <input type="number" class="form-control" name="duration" value="${milestone.duration || ''}">
                </div>
                <div class="mb-3 annuity-fields" style="display: ${milestone.disbursement_type ? 'block' : 'none'}">
                    <label class="form-label">Rate of Return (%)</label>
                    <input type="number" class="form-control" name="rate_of_return" value="${milestone.rate_of_return ? milestone.rate_of_return * 100 : ''}" step="0.1">
                </div>
                <button type="submit" class="btn btn-primary">Save</button>
                <button type="button" class="btn btn-danger delete-milestone">Delete</button>
            </form>
        </div>
    `);
    
    $('#milestoneForms').append(form);
    
    // Add event listener for milestone type changes
    form.find('[name="milestone_type"]').on('change', function() {
        updateAnnuityFieldsVisibility(form);
    });
    
    // Add event listener for disbursement type changes
    form.find('[name="disbursement_type"]').on('change', function() {
        updateAnnuityFieldsVisibility(form);
    });
    
    // Add event listeners for the new form
    form.find('.milestone-form-content').on('submit', handleMilestoneUpdate);
    form.find('.delete-milestone').on('click', handleMilestoneDelete);
}

function updateAnnuityFieldsVisibility(form) {
    const milestoneType = form.find('[name="milestone_type"]').val();
    const disbursementType = form.find('[name="disbursement_type"]').val();
    
    // Show payment field for Asset and Liability types
    form.find('.payment-field').toggle(['Asset', 'Liability'].includes(milestoneType));
    
    // Show all annuity fields if disbursement type is selected
    const showAnnuityFields = disbursementType !== null;
    form.find('.annuity-fields').toggle(showAnnuityFields);
    
    // Hide duration field if type is Perpetuity
    if (disbursementType === 'Perpetuity') {
        form.find('.duration-field').hide();
    } else if (showAnnuityFields) {
        form.find('.duration-field').show();
    }
}

function handleMilestoneUpdate(e) {
    e.preventDefault();
    const form = $(e.target);
    const milestoneId = form.closest('.milestone-form').data('id');
    const milestone = milestones.find(m => m.id === milestoneId);
    
    if (milestone) {
        const milestoneType = form.find('[name="milestone_type"]').val();
        const disbursementType = form.find('[name="disbursement_type"]').val();
        const updatedMilestone = {
            name: form.find('[name="name"]').val(),
            age_at_occurrence: parseInt(form.find('[name="age_at_occurrence"]').val()),
            milestone_type: milestoneType,
            disbursement_type: disbursementType,
            amount: parseFloat(form.find('[name="amount"]').val())
        };
        
        // Add payment field for Asset and Liability types
        if (['Asset', 'Liability'].includes(milestoneType)) {
            updatedMilestone.payment = parseFloat(form.find('[name="payment"]').val()) || null;
        }
        
        if (disbursementType) {
            updatedMilestone.occurrence = form.find('[name="occurrence"]').val();
            updatedMilestone.rate_of_return = parseFloat(form.find('[name="rate_of_return"]').val()) / 100;
            
            if (disbursementType === 'Fixed Duration') {
                updatedMilestone.duration = parseInt(form.find('[name="duration"]').val());
            } else {  // Perpetuity
                updatedMilestone.duration = null;
            }
        } else {
            updatedMilestone.occurrence = null;
            updatedMilestone.duration = null;
            updatedMilestone.rate_of_return = null;
        }
        
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