// Global variables
let currentAge = 0;
let milestones = [];

// Initialize the application
$(document).ready(function() {
    initializeEventListeners();
    loadProfile();
    setupSidebarToggle();
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
            // Refresh the page to ensure proper ordering of milestone markers and labels
            window.location.reload();
        },
        error: function(error) {
            console.error('Error saving profile:', error);
            alert('Error saving profile. Please try again.');
        }
    });
}

// Milestone Functions
function createDefaultMilestones() {
    // Create all milestones in parallel and wait for all to complete
    Promise.all([
        // Create Current Assets milestone (order 0)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Current Liquid Assets',
                age_at_occurrence: currentAge,
                milestone_type: 'Asset',
                disbursement_type: 'Perpetuity',
                amount: 30000,
                payment: 5000,
                occurrence: 'Yearly',
                rate_of_return: 0.07,  // 7%
                order: 2
            })
        }),
        // Create Current Debt milestone (order 1)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Current Debt',
                age_at_occurrence: currentAge,
                milestone_type: 'Liability',
                disbursement_type: 'Fixed Duration',
                amount: 35000,
                payment: 500,
                occurrence: 'Monthly',
                rate_of_return: 0.07,  // 7%
                duration: 120,
                order: 3
            })
        }),
        // Create Current Income milestone (order 2)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Current Salary (incl. Bonus, Side Hustle, etc.)',
                age_at_occurrence: currentAge,
                milestone_type: 'Income',
                disbursement_type: 'Fixed Duration',
                amount: 50000,
                occurrence: 'Yearly',
                duration: 70 - currentAge,  // Auto-calculate duration
                rate_of_return: 0.02,  // 2%
                order: 0
            })
        }),
        // Create Current Expense milestone (order 3)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Current Average Expenses',
                age_at_occurrence: currentAge,
                milestone_type: 'Expense',
                disbursement_type: 'Fixed Duration',
                amount: 3000,
                occurrence: 'Monthly',
                duration: 70 - currentAge,  // Auto-calculate duration
                rate_of_return: 0.03,  // 2%
                order: 1
            })
        }),
        // Create Retirement milestone (order 4)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Retirement',
                age_at_occurrence: 70,
                milestone_type: 'Expense',
                disbursement_type: 'Fixed Duration',
                amount: 60000,
                occurrence: 'Yearly',
                duration: 30,  // 4 years
                rate_of_return: 0.06,  // 4%
                order: 4
            })
        }),
        // Create Long Term Care (self) milestone (order 5)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Long Term Care (self)',
                age_at_occurrence: 96,
                milestone_type: 'Expense',
                disbursement_type: 'Fixed Duration',
                amount: 6000,
                occurrence: 'Monthly',
                duration: 48,  // 4 years
                rate_of_return: 0.04,  // 4%
                order: 5
            })
        }),
        // Create Inheritance milestone (order 6)
        $.ajax({
            url: '/api/milestones',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: 'Inheritance',
                age_at_occurrence: 100,
                milestone_type: 'Expense',
                disbursement_type: 'Fixed Duration',
                amount: 10000,
                occurrence: 'Monthly',
                duration: 1,
                rate_of_return: 0.0,
                order: 6
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
            // Log the received milestones and their order
            console.log('Received milestones:', response.map(m => ({ name: m.name, order: m.order })));
            
            // Use the order from the backend response
            milestones = response;
            updateTimeline();
            
            // Update the NPV chart
            window.npvChart.updateChart(milestones);
            
            // Clear existing milestone forms before creating new ones
            $('#milestoneForms').empty();
            milestones.forEach(createMilestoneForm);
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
        rate_of_return: 0.0,
        order: milestones.length  // Set order to be after all existing milestones
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
            <div class="milestone-header" draggable="true">
                <h3>${milestone.name}</h3>
                <div class="milestone-header-buttons">
                    <button type="button" class="btn btn-outline-primary btn-sm save-milestone">
                        <i class="fas fa-save"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger btn-sm delete-milestone">
                        <i class="fas fa-trash"></i>
                    </button>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
            </div>
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
                    <label class="form-label">
                        Payment
                        <span class="tooltip-container">
                            <i class="fas fa-info-circle info-icon"></i>
                            <span class="tooltip-text">Enter negative value for asset withdrawals / enter positive value for liability payments</span>
                        </span>
                    </label>
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
            </form>
        </div>
    `);
    
    $('#milestoneForms').append(form);
    
    // Add drag and drop event listeners to the header
    const header = form.find('.milestone-header');
    header.on('dragstart', function(e) {
        e.originalEvent.dataTransfer.setData('text/plain', form.data('id'));
        form.addClass('dragging');
    });
    
    header.on('dragend', function() {
        form.removeClass('dragging');
    });
    
    form.on('dragover', function(e) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'move';
    });
    
    form.on('drop', function(e) {
        e.preventDefault();
        const draggedId = e.originalEvent.dataTransfer.getData('text/plain');
        const draggedForm = $(`.milestone-form[data-id="${draggedId}"]`);
        const dropForm = $(this);
        
        if (draggedId !== dropForm.data('id')) {
            // Reorder the milestones array
            const draggedIndex = milestones.findIndex(m => m.id === parseInt(draggedId));
            const dropIndex = milestones.findIndex(m => m.id === dropForm.data('id'));
            
            const [draggedMilestone] = milestones.splice(draggedIndex, 1);
            milestones.splice(dropIndex, 0, draggedMilestone);
            
            // Update order for all milestones
            const updatePromises = milestones.map((milestone, index) => {
                milestone.order = index;
                // Send update to server
                return $.ajax({
                    url: `/api/milestones/${milestone.id}`,
                    method: 'PUT',
                    contentType: 'application/json',
                    data: JSON.stringify({ order: index })
                });
            });
            
            // Wait for all updates to complete, then refresh the page
            Promise.all(updatePromises)
                .then(() => {
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error updating milestone order:', error);
                    alert('Error updating milestone order. Please try again.');
                });
        }
    });
    
    // Add hover handlers for the entire milestone form
    form.hover(
        function() { // mouseenter
            const milestoneId = $(this).data('id');
            highlightMilestone(milestoneId);
        },
        function() { // mouseleave
            const milestoneId = $(this).data('id');
            unhighlightMilestone(milestoneId);
        }
    );
    
    // Add click handler for the header to toggle the form
    header.on('click', function(e) {
        // Only toggle if not dragging and not clicking buttons
        if (e.type === 'click' && !form.hasClass('dragging') && !$(e.target).is('button')) {
            form.toggleClass('expanded');
            form.find('.toggle-icon').toggleClass('expanded');
        }
    });
    
    // Add event listener for milestone type changes
    form.find('[name="milestone_type"]').on('change', function() {
        updateAnnuityFieldsVisibility(form);
    });
    
    // Add event listener for disbursement type changes
    form.find('[name="disbursement_type"]').on('change', function() {
        updateAnnuityFieldsVisibility(form);
    });
    
    // Add event listeners for the new form
    form.find('.save-milestone').on('click', function() {
        handleMilestoneUpdate({ preventDefault: () => {} }, form.find('.milestone-form-content'));
    });
    form.find('.delete-milestone').on('click', handleMilestoneDelete);
}

function highlightMilestone(milestoneId) {
    $(`.milestone-marker[data-id="${milestoneId}"]`).addClass('highlighted');
    $(`.milestone-label[data-id="${milestoneId}"]`).addClass('highlighted');
    $(`.milestone-form[data-id="${milestoneId}"]`).addClass('highlighted');
    $(`.npv-bar[data-id="${milestoneId}"]`).addClass('highlighted');
    $(`.npv-label[data-id="${milestoneId}"]`).addClass('highlighted');
}

function unhighlightMilestone(milestoneId) {
    $(`.milestone-marker[data-id="${milestoneId}"]`).removeClass('highlighted');
    $(`.milestone-label[data-id="${milestoneId}"]`).removeClass('highlighted');
    $(`.milestone-form[data-id="${milestoneId}"]`).removeClass('highlighted');
    $(`.npv-bar[data-id="${milestoneId}"]`).removeClass('highlighted');
    $(`.npv-label[data-id="${milestoneId}"]`).removeClass('highlighted');
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

function handleMilestoneUpdate(e, form) {
    e.preventDefault();
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
                // Update the NPV chart
                window.npvChart.updateChart(milestones);
                // Refresh the page to update milestone headers
                window.location.reload();
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
            // Remove the milestone from the local array
            milestones = milestones.filter(m => m.id !== milestoneId);
            // Update the NPV chart
            window.npvChart.updateChart(milestones);
            // Refresh the page to reset timeline spacing
            window.location.reload();
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

function setupSidebarToggle() {
    const sidebar = $('.sidebar');
    const mainContent = $('.main-content');
    const hideButton = $('.sidebar-header .toggle-icon');
    const showButton = $('.show-sidebar-button');
    
    hideButton.on('click', function() {
        sidebar.toggleClass('hidden');
        mainContent.toggleClass('expanded');
    });
    
    showButton.on('click', function() {
        sidebar.toggleClass('hidden');
        mainContent.toggleClass('expanded');
    });
}

function updateCharts() {
    // Update NPV chart
    fetch('/api/milestones')
        .then(response => response.json())
        .then(milestones => {
            window.npvChart.updateChart(milestones);
        });
    
    // Update net worth chart
    fetch('/api/net-worth')
        .then(response => response.json())
        .then(netWorthData => {
            console.log('Net worth data:', netWorthData);
            if (window.netWorthChart) {
                console.log('Updating net worth chart with data');
                window.netWorthChart.updateChart(netWorthData);
            } else {
                console.error('Net worth chart not initialized');
            }
        })
        .catch(error => {
            console.error('Error fetching net worth data:', error);
        });
}

// Add event listeners for milestone changes
document.addEventListener('milestoneCreated', updateCharts);
document.addEventListener('milestoneUpdated', updateCharts);
document.addEventListener('milestoneDeleted', updateCharts);

// Initial chart update
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing charts');
    updateCharts();
}); 