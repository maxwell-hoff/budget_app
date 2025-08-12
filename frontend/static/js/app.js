// Global variables
let currentAge = 0;
let milestones = [];
let globalScenarioValues = {};
// Track the most recent loadMilestones request so we can ignore stale responses
let milestonesLoadCounter = 0;

// Add after global variable declarations (around line 1-6)
const INFLATION_RATE = 0.02; // Default 2% inflation – update easily to change default conversion

// Initialize the application
$(document).ready(function() {
    console.log('Document ready, initializing application...');
    initializeEventListeners();
    loadProfile();

    // Attempt to autoplay hero video when ready
    const heroVid = document.getElementById('heroVideo');
    if (heroVid) {
        heroVid.muted = true; // satisfy autoplay policy
        const tryPlay = () => {
            heroVid.play().catch(() => {
                // If automatic playback fails, try again after user interaction
                const unlock = () => {
                    heroVid.play().catch(()=>{});
                    window.removeEventListener('click', unlock);
                    window.removeEventListener('touchstart', unlock);
                };
                window.addEventListener('click', unlock, {once: true});
                window.addEventListener('touchstart', unlock, {once: true});
            });
        };
        // If not ready yet, wait for canplay
        if (heroVid.readyState >= 3) {
            tryPlay();
        } else {
            heroVid.addEventListener('canplay', tryPlay, {once: true});
        }
    }
    setupTabSwitching();
    
    // Ensure milestone details section exists
    if ($('#milestoneDetails').length === 0) {
        console.error('Milestone details section not found!');
    } else {
        console.log('Milestone details section found');
    }
    
    if ($('#milestoneForms').length === 0) {
        console.error('Milestone forms container not found!');
    } else {
        console.log('Milestone forms container found');
    }

    // Fetch all scenario-parameter values globally for tooltips
    fetch('/api/scenario-parameter-values')
        .then(res => res.json())
        .then(data => { globalScenarioValues = data; })
        .catch(err => console.warn('Could not fetch global scenario values', err));

    // Initialize bootstrap tooltips for sidebar icons
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('.nav-button[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));

    // CTA interactions
    const goToProfile = () => {
        document.querySelector('.nav-button[data-tab="tab-profile"]').click();
        const formEl = document.getElementById('userProfileForm');
        if (formEl) { formEl.scrollIntoView({behavior: 'smooth', block: 'start'}); }
    };
    const goToAnalysis = () => {
        document.querySelector('.nav-button[data-tab="tab-analysis"]').click();
        const chartsEl = document.getElementById('net-worth-chart');
        if (chartsEl) { chartsEl.scrollIntoView({behavior: 'smooth', block: 'start'}); }
    };
    const ctaStart = document.getElementById('cta-get-started');
    const ctaDemo = document.getElementById('cta-see-demo');
    if (ctaStart) { ctaStart.addEventListener('click', goToProfile); }
    if (ctaDemo) { ctaDemo.addEventListener('click', goToAnalysis); }

    // Hide scroll indicator after brief delay or on scroll
    const indicator = document.getElementById('scrollIndicator');
    if (indicator) {
        const hideIndicator = () => indicator.style.display = 'none';
        setTimeout(hideIndicator, 3500);
        window.addEventListener('scroll', hideIndicator, { once: true });
    }

    // Full-page scroll snapping threshold + reveal-on-scroll
    const mainContainer = document.querySelector('.main-container');
    if (mainContainer) {
        const thresholdAttr = mainContainer.getAttribute('data-fullpage-threshold');
        const fullpageThreshold = Math.max(0, parseInt(thresholdAttr || '400', 10) || 0);

        const applySnapState = () => {
            if (mainContainer.scrollTop >= fullpageThreshold) {
                mainContainer.classList.add('snap-enabled');
            } else {
                mainContainer.classList.remove('snap-enabled');
            }
        };

        // Reveal-on-scroll using IntersectionObserver scoped to the container
        let hasUserScrolled = false;
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const isHeroOverlay = entry.target.matches('.home-video-overlay .overlay-inner.reveal');
                // Keep hero overlay hidden until the user scrolls
                if (isHeroOverlay && !hasUserScrolled) return;
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { root: null, threshold: 0.15 });

        const revealTargets = mainContainer.querySelectorAll('.reveal');
        revealTargets.forEach(el => revealObserver.observe(el));

        const revealNowIfInViewport = () => {
            // Fallback check: mark any reveal elements visible if they are in viewport
            const vpH = window.innerHeight || document.documentElement.clientHeight;
            revealTargets.forEach(el => {
                if (el.classList.contains('visible')) return;
                const rect = el.getBoundingClientRect();
                const inView = rect.top < vpH * 0.9 && rect.bottom > vpH * 0.1;
                if (inView && (hasUserScrolled || !el.closest('.home-video-overlay'))) {
                    el.classList.add('visible');
                    revealObserver.unobserve(el);
                }
            });
        };

        const onContainerScroll = () => {
            if (!hasUserScrolled && mainContainer.scrollTop > 2) {
                hasUserScrolled = true;
                // Re-observe all targets once to force a fresh intersection
                // calculation now that reveals are allowed.
                revealTargets.forEach(el => {
                    revealObserver.unobserve(el);
                    revealObserver.observe(el);
                });
                // Ensure hero overlay becomes visible once user has scrolled
                const heroOverlayInner = document.querySelector('.home-video-overlay .overlay-inner.reveal');
                if (heroOverlayInner) heroOverlayInner.classList.add('visible');
            }
            applySnapState();
            revealNowIfInViewport();
        };

        mainContainer.addEventListener('scroll', onContainerScroll, { passive: true });
        window.addEventListener('scroll', onContainerScroll, { passive: true });
        // Mark that the user scrolled even if container didn't move (e.g. wheel over hero)
        const markScrolled = () => {
            if (hasUserScrolled) return;
            hasUserScrolled = true;
            const heroOverlayInner = document.querySelector('.home-video-overlay .overlay-inner.reveal');
            if (heroOverlayInner) heroOverlayInner.classList.add('visible');
            // Kick observer
            revealTargets.forEach(el => {
                revealObserver.unobserve(el);
                revealObserver.observe(el);
            });
        };
        window.addEventListener('wheel', markScrolled, { passive: true });
        window.addEventListener('touchmove', markScrolled, { passive: true });
        window.addEventListener('keydown', (e) => {
            if (['ArrowDown','PageDown','Space'].includes(e.code)) markScrolled();
        });
        window.addEventListener('resize', revealNowIfInViewport, { passive: true });
        // Initialize state on load
        applySnapState();
        // Initial pass to reveal anything already in view (non-hero)
        revealNowIfInViewport();
    }

    // Accounts input mode toggle
    const uploadPane = document.getElementById('accounts-upload-pane');
    const manualPane = document.getElementById('accounts-manual-pane');
    const modeUpload = document.getElementById('modeUpload');
    const modeManual = document.getElementById('modeManual');
    if (modeUpload && modeManual && uploadPane && manualPane) {
        const updateMode = () => {
            const manual = modeManual.checked;
            manualPane.style.display = manual ? 'block' : 'none';
            uploadPane.style.display = manual ? 'none' : 'block';
        };
        modeUpload.addEventListener('change', updateMode);
        modeManual.addEventListener('change', updateMode);
        updateMode();
    }

    // Manual accounts UI
    const accountsList = document.getElementById('accountsList');
    const addBtn = document.getElementById('addAccountBtn');
    const saveBtn = document.getElementById('saveAccountsBtn');
    const template = document.getElementById('accountRowTemplate');
    const sumCash = document.getElementById('sumCash');
    const sumInvestments = document.getElementById('sumInvestments');
    const sumLiabilities = document.getElementById('sumLiabilities');
    const sumNet = document.getElementById('sumNet');

    const ACCOUNT_STORAGE_KEY = 'manualAccounts';

    function loadAccountsFromStorage() {
        try {
            const raw = localStorage.getItem(ACCOUNT_STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch { return []; }
    }
    function saveAccountsToStorage(data) {
        localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify(data));
    }
    function currency(n) {
        const val = isNaN(n) || n === '' || n === null ? 0 : Number(n);
        return val.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
    }

    function categorize(type) {
        const t = (type || '').toLowerCase();
        if (t.includes('checking') || t.includes('savings')) return 'cash';
        if (t.includes('brokerage') || t.includes('retirement') || t.includes('invest')) return 'investments';
        if (t.includes('credit') || t.includes('loan') || t.includes('liabil')) return 'liabilities';
        return 'cash';
    }

    function recalcSummary() {
        const rows = accountsList ? accountsList.querySelectorAll('.account-row') : [];
        let cash = 0, invest = 0, liab = 0;
        rows.forEach(row => {
            const type = row.querySelector('.account-type')?.value;
            const bal = parseFloat(row.querySelector('.account-balance')?.value);
            const cat = categorize(type);
            const v = isNaN(bal) ? 0 : bal;
            if (cat === 'cash') cash += v;
            else if (cat === 'investments') invest += v;
            else liab += v;
        });
        if (sumCash) sumCash.textContent = currency(cash);
        if (sumInvestments) sumInvestments.textContent = currency(invest);
        if (sumLiabilities) sumLiabilities.textContent = currency(liab);
        if (sumNet) sumNet.textContent = currency(cash + invest - liab);
    }

    function bindRowEvents(row) {
        const inputs = row.querySelectorAll('input, select');
        inputs.forEach(inp => inp.addEventListener('input', recalcSummary));
        const del = row.querySelector('.delete-account');
        if (del) {
            del.addEventListener('click', (e) => {
                e.preventDefault();
                row.remove();
                recalcSummary();
            });
        }
    }

    function addAccountRow(data = {}) {
        if (!template || !accountsList) return;
        const fragment = template.content.cloneNode(true);
        const row = fragment.querySelector('.account-row');
        row.querySelector('.account-type').value = data.type || 'Checking';
        row.querySelector('.account-institution').value = data.institution || '';
        row.querySelector('.account-name').value = data.name || '';
        row.querySelector('.account-balance').value = data.balance != null ? data.balance : '';
        bindRowEvents(row);
        accountsList.appendChild(fragment);
        recalcSummary();
    }

    function serializeAccounts() {
        if (!accountsList) return [];
        return Array.from(accountsList.querySelectorAll('.account-row')).map(row => ({
            type: row.querySelector('.account-type').value,
            institution: row.querySelector('.account-institution').value,
            name: row.querySelector('.account-name').value,
            balance: parseFloat(row.querySelector('.account-balance').value) || 0,
        }));
    }

    if (addBtn) {
        addBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addAccountRow();
        });
    }
    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const data = serializeAccounts();
            saveAccountsToStorage(data);
            // Placeholder: could POST to backend if/when endpoint exists
            // fetch('/api/accounts', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ accounts: data }) })
            //     .then(r=>r.json()).then(()=>{/* success */}).catch(()=>{/* error */});
        });
    }

    // Initialize list from storage
    if (accountsList && template) {
        const saved = loadAccountsFromStorage();
        if (saved.length === 0) {
            addAccountRow({ type: 'Checking', name: 'Checking', institution: '', balance: 0 });
        } else {
            saved.forEach(addAccountRow);
        }
    }
});

// Event Listeners
function initializeEventListeners() {
    console.log('Initializing event listeners...');
    // User profile form
    $('#userProfileForm').on('submit', handleProfileSubmit);
    $('#birthday').on('change', calculateAge);
    
    // Milestone controls
    $('#addMilestone').on('click', addNewMilestone);
    
    // Bank statement upload
    $('#statementUploadForm').on('submit', handleStatementUpload);
}

// Setup Tab Switching
function setupTabSwitching() {
    $('.nav-button').on('click', function() {
        const tabId = $(this).data('tab');

        // Update button active state
        $('.nav-button').removeClass('active');
        $(this).addClass('active');

        // Show the selected tab and hide others
        $('.tab-pane').removeClass('active');
        $('#' + tabId).addClass('active');

        // Toggle scenario bar visibility (only visible on Milestones tab)
        if (tabId === 'tab-milestones') {
            $('.scenario-bar').show();
        } else {
            $('.scenario-bar').hide();
        }

        // Restart hero video if Home tab becomes active
        if (tabId === 'tab-home') {
            const vid = document.querySelector('.home-video');
            if (vid) {
                try {
                    vid.currentTime = 0;
                    vid.play();
                } catch (err) { /* no-op */ }
            }
        }

        // If Milestones tab became active, refresh timeline so it renders with correct width
        if (tabId === 'tab-milestones' && window.timeline) {
            // Small timeout ensures element has become visible before measuring widths
            setTimeout(() => window.timeline.updateTimeline(), 50);
        }

        // If Analysis tab became active, (re)load charts so they render correctly
        if (tabId === 'tab-analysis') {
            setTimeout(() => updateCharts(), 50);
        }
    });
}

// After definition of setupTabSwitching, ensure charts update if analysis tab pre-selected (unlikely but safe)
$(document).ready(function(){
    if ($('.nav-button.active').data('tab') === 'tab-analysis') {
        updateCharts();
    }
});

// User Profile Functions
function loadProfile() {
    console.log('Loading profile...');
    $.ajax({
        url: '/api/profile',
        method: 'GET',
        success: function(response) {
            console.log('Profile loaded:', response);
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
                console.log('No birthday found, showing profile form');
                // Show the profile form if no birthday is saved
                $('#profileForm').show();
                $('#profileInfo').hide();
            }
        },
        error: function(error) {
            console.log('Error loading profile:', error);
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
    
    console.log('Submitting profile with birthday:', birthday);
    
    // Save profile
    $.ajax({
        url: '/api/profile',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ birthday: birthday }),
        success: function(response) {
            console.log('Profile saved successfully:', response);
            
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
            
            // Update the timeline with the loaded birthday
            window.timeline.updateTimeline();
            
            // Load milestones after profile is created
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
    // Check if default milestones already exist
    const existingCurrentMilestone = milestones.find(m => m.name === 'Current');
    const existingInheritanceMilestone = milestones.find(m => m.name === 'Inheritance');
    
    if (existingCurrentMilestone && existingInheritanceMilestone) {
        console.log('Default milestones already exist');
        return;
    }
    
    const currentAge = parseInt($('#currentAge').val());
    
    // Create Current milestone
    const newCurrentMilestone = {
        name: 'Current',
        age_at_occurrence: currentAge,
        milestone_type: 'Asset',
        disbursement_type: 'Perpetuity',
        amount: 0,
        amount_value_type: 'FV',
        payment: null,
        payment_value_type: 'FV',
        occurrence: 'Yearly',
        duration: null,
        rate_of_return: 0.0,
        order: 0
    };
    
    // Create Inheritance milestone
    const newInheritanceMilestone = {
        name: 'Inheritance',
        age_at_occurrence: 100,
        milestone_type: 'Asset',
        disbursement_type: 'Perpetuity',
        amount: 10000,
        amount_value_type: 'FV',
        payment: null,
        payment_value_type: 'FV',
        occurrence: 'Yearly',
        duration: null,
        rate_of_return: 0.0,
        order: 1
    };
    
    // Create parent milestones first
    $.ajax({
        url: '/api/parent-milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: newCurrentMilestone.name,
            min_age: newCurrentMilestone.age_at_occurrence,
            milestone_data: newCurrentMilestone
        }),
        success: function(currentParentResponse) {
            // Add parent milestone ID to current milestone
            newCurrentMilestone.parent_milestone_id = currentParentResponse.id;
            
            // Create current milestone
            $.ajax({
                url: '/api/milestones',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(newCurrentMilestone),
                success: function(currentResponse) {
                    // Create inheritance parent milestone
                    $.ajax({
                        url: '/api/parent-milestones',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({
                            name: newInheritanceMilestone.name,
                            min_age: newInheritanceMilestone.age_at_occurrence,
                            milestone_data: newInheritanceMilestone
                        }),
                        success: function(inheritanceParentResponse) {
                            // Add parent milestone ID to inheritance milestone
                            newInheritanceMilestone.parent_milestone_id = inheritanceParentResponse.id;
                            
                            // Create inheritance milestone
                            $.ajax({
                                url: '/api/milestones',
                                method: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify(newInheritanceMilestone),
                                success: function(inheritanceResponse) {
                                    // Load milestones and update UI
                                    loadMilestones();
                                },
                                error: function(error) {
                                    console.error('Error creating inheritance milestone:', error);
                                    alert('Error creating inheritance milestone. Please try again.');
                                }
                            });
                        },
                        error: function(error) {
                            console.error('Error creating inheritance parent milestone:', error);
                            alert('Error creating inheritance parent milestone. Please try again.');
                        }
                    });
                },
                error: function(error) {
                    console.error('Error creating current milestone:', error);
                    alert('Error creating current milestone. Please try again.');
                }
            });
        },
        error: function(error) {
            console.error('Error creating current parent milestone:', error);
            alert('Error creating current parent milestone. Please try again.');
        }
    });
}

function loadMilestones() {
    // Increment counter and capture the id for this invocation
    const loadId = ++milestonesLoadCounter;
    console.log('Loading milestones...');
    const scenarioId = $('#scenarioSelect').val();
    const subScenarioId = $('#subScenarioSelect').val();
    let url = '/api/milestones';
    const params = [];
    if (scenarioId) params.push(`scenario_id=${scenarioId}`);
    if (subScenarioId) params.push(`sub_scenario_id=${subScenarioId}`);
    if (params.length) {
        url += '?' + params.join('&');
    }
    $.ajax({
        url: url,
        method: 'GET',
        success: function(response) {
            // Ignore if this is not the latest request
            if (loadId !== milestonesLoadCounter) {
                console.log('Stale milestone load ignored');
                return;
            }
            console.log('Milestones loaded:', response);
            milestones = response;
            
            // Clear existing milestone forms
            $('#milestoneForms').empty();
            console.log('Cleared milestone forms container');
            
            if (milestones.length === 0) {
                console.log('No milestones found');
                // Add a message when there are no milestones
                $('#milestoneForms').html('<div class="alert alert-info">No milestones yet. Click the + button in the timeline to add your first milestone.</div>');
                return;
            }
            
            // Load parent milestones
            $.ajax({
                url: scenarioId ? `/api/parent-milestones?scenario_id=${scenarioId}` : '/api/parent-milestones',
                method: 'GET',
                success: function(parentMilestones) {
                    // Ignore if this is not the latest request (another load triggered after this one started)
                    if (loadId !== milestonesLoadCounter) {
                        console.log('Stale parent milestone load ignored');
                        return;
                    }
                    console.log('Parent milestones loaded:', parentMilestones);

                    // Deduplicate parent milestones by ID in case the API returns duplicates (e.g., SQL join duplicates)
                    const uniqueParentsMap = {};
                    parentMilestones.forEach(pm => {
                        if (!uniqueParentsMap[pm.id]) {
                            uniqueParentsMap[pm.id] = pm;
                        }
                    });
                    const uniqueParentMilestones = Object.values(uniqueParentsMap);
                    console.log('Unique parent milestones:', uniqueParentMilestones);
                    
                    // Group milestones by their parent_milestone_id
                    const milestoneGroups = {};
                    milestones.forEach(milestone => {
                        const parentId = milestone.parent_milestone_id;
                        if (!milestoneGroups[parentId]) {
                            milestoneGroups[parentId] = [];
                        }
                        milestoneGroups[parentId].push(milestone);
                    });
                    
                    console.log('Milestone groups:', milestoneGroups);
                    
                    // Create forms for each parent milestone and its sub-milestones
                    uniqueParentMilestones.forEach(parentMilestone => {
                        // Determine sub-milestones for this parent first
                        const subMilestones = milestoneGroups[parentMilestone.id] || [];

                        // If there is exactly one sub-milestone, just render that sub-milestone directly to avoid duplicate-looking entries.
                        if (subMilestones.length === 1) {
                            const soloForm = createMilestoneForm(subMilestones[0]);
                            $('#milestoneForms').append(soloForm);
                            console.log('Appended single sub-milestone for', parentMilestone.name);
                            return; // Skip rendering parent container
                        }

                        // Otherwise render a parent container followed by its sub-milestones
                        // Create a parent milestone form (acts as a visual group header)
                        const parentForm = createMilestoneForm({
                            id: parentMilestone.id,
                            name: parentMilestone.name,
                            age_at_occurrence: parentMilestone.min_age,
                            milestone_type: 'Group',
                            disbursement_type: 'Fixed Duration',
                            amount: 0,
                            payment: 0,
                            occurrence: 'Yearly',
                            duration: parentMilestone.max_age - parentMilestone.min_age,
                            rate_of_return: 0,
                            order: 0
                        });

                        // Add sub-milestones container
                        const subMilestonesContainer = $('<div class="sub-milestones-container"></div>');
                        parentForm.append(subMilestonesContainer);
                        
                        // Add sub-milestones for this parent
                        subMilestones.forEach(milestone => {
                            const subForm = createMilestoneForm(milestone);
                            subForm.addClass('sub-milestone-form');
                            subMilestonesContainer.append(subForm);
                        });
                        
                        // Append the parent form to the milestone forms container
                        $('#milestoneForms').append(parentForm);
                        console.log('Appended parent form for', parentMilestone.name);
                    });
                    
                    // Update the timeline with the loaded milestones
                    updateTimeline();
                },
                error: function(error) {
                    console.error('Error loading parent milestones:', error);
                    $('#milestoneForms').html('<div class="alert alert-danger">Error loading milestones. Please try refreshing the page.</div>');
                }
            });
        },
        error: function(error) {
            console.error('Error loading milestones:', error);
            // Show error message when milestone loading fails
            $('#milestoneForms').html('<div class="alert alert-danger">Error loading milestones. Please try refreshing the page.</div>');
        }
    });
}

function addNewMilestone() {
    const currentAge = parseInt($('#currentAge').val());
    
    // Create new milestone
    const milestone = {
        name: 'New Milestone',
        age_at_occurrence: currentAge + 5,
        milestone_type: 'Expense',
        disbursement_type: 'Fixed Duration',
        amount: 0,
        amount_value_type: 'FV',
        payment: null,
        payment_value_type: 'FV',
        occurrence: 'Yearly',
        duration: 1,
        rate_of_return: 0.0,
        order: milestones.length, // Set order to be after all existing milestones
        scenario_id: parseInt($('#scenarioSelect').val()) || 1,
        scenario_name: $('#scenarioSelect option:selected').text() || 'Base Scenario',
        sub_scenario_id: parseInt($('#subScenarioSelect').val()) || 1,
        sub_scenario_name: $('#subScenarioSelect option:selected').text() || 'Base Sub-Scenario'
    };
    
    // Create parent milestone first
    $.ajax({
        url: '/api/parent-milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            name: milestone.name,
            min_age: milestone.age_at_occurrence,
            milestone_data: milestone
        }),
        success: function(parentResponse) {
            // Add parent milestone ID to the milestone
            milestone.parent_milestone_id = parentResponse.id;
            
            // Create the milestone
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
        },
        error: function(error) {
            console.error('Error creating parent milestone:', error);
            alert('Error creating parent milestone. Please try again.');
        }
    });
}

function updateTimeline() {
    // Clear existing milestones
    $('#timeline-milestones').empty();
    
    // Load parent milestones
    const scenarioId = $('#scenarioSelect').val();
    $.ajax({
        url: scenarioId ? `/api/parent-milestones?scenario_id=${scenarioId}` : '/api/parent-milestones',
        method: 'GET',
        success: function(parentMilestones) {
            // Add each parent milestone to the timeline
            parentMilestones.forEach(milestone => {
                window.timeline.addParentMilestone(milestone);
            });
        },
        error: function(error) {
            console.error('Error loading parent milestones:', error);
        }
    });
}

function createMilestoneForm(milestone) {
    console.log('Creating milestone form for:', milestone);
    
    // Helper to generate a goal checkbox HTML snippet next to a parameter label
    const goalCheckbox = (param) => {
        const checked = milestone.goal_parameters && milestone.goal_parameters.includes(param) ? 'checked' : '';
        return `<input type="checkbox" class="goal-checkbox ms-2" data-param="${param}" ${checked} title="Mark as goal">`;
    };
    
    // Helper to generate scenario control HTML (button + dropdown) for a parameter
    const scenarioControls = (param) => {
        // Merge local milestone-specific values with globally known ones
        const localVals = (milestone.scenario_parameter_values && milestone.scenario_parameter_values[param]) || [];
        const globalVals = globalScenarioValues[param] || [];
        const values = Array.from(new Set([...localVals, ...globalVals]));
        const listItems = values.map(v => `
            <li>
                <span class="dropdown-item d-flex justify-content-between align-items-center" data-value="${v}">
                    ${v}
                    <i class="fas fa-times text-danger delete-scenario-value" data-param="${param}" data-value="${v}"></i>
                </span>
            </li>`).join('');
        return `
            <div class="btn-group ms-2 scenario-values-group" data-param="${param}">
                <button type="button" class="btn btn-outline-secondary btn-sm add-scenario-value" data-param="${param}">Add as Scenario</button>
                <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                    Values
                </button>
                <ul class="dropdown-menu scenario-values-list" data-param="${param}">${listItems}</ul>
            </div>`;
    };
    
    const isInheritance = milestone.name === 'Inheritance';

    // --- Dual Amount Inputs ---------------------------------------------------
    const yearsDelta = milestone.age_at_occurrence - currentAge;
    const growthFactor = Math.pow(1 + INFLATION_RATE, yearsDelta);

    const amt = milestone.amount || 0;
    const amtType = milestone.amount_value_type || 'FV';

    let fvVal, pvVal;
    if (amtType === 'PV') {
        // The stored *amount* represents the present-value figure.
        pvVal = amt.toFixed(2);
        fvVal = (amt * growthFactor).toFixed(2);
    } else {
        // The stored *amount* already represents the future-value at the milestone age.
        fvVal = amt.toFixed(2);
        pvVal = (amt / growthFactor).toFixed(2);
    }
    
    const paymentDisplay = milestone.payment || '';
    
    const form = $(`
        <div class="milestone-form" data-id="${milestone.id}">
            <div class="milestone-header" draggable="true">
                <h3 contenteditable="true" class="editable-header">${milestone.name}</h3>
                <div class="milestone-header-buttons">
                    ${milestone.milestone_type === 'Group' ? `
                        <button type="button" class="btn btn-outline-success btn-sm add-sub-milestone">
                            <i class="fas fa-plus"></i>
                        </button>
                    ` : ''}
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
                    <label class="form-label">Age at Occurrence${goalCheckbox('age_at_occurrence')}</label>
                    <div class="d-flex align-items-center">
                        <input type="number" class="form-control age-input" name="age_at_occurrence" value="${milestone.age_at_occurrence}" ${milestone.start_after_milestone ? 'disabled' : ''}>
                        ${scenarioControls('age_at_occurrence')}
                    </div>
                    <div class="form-check mt-2">
                        <input class="form-check-input dynamic-start-checkbox" type="checkbox" ${milestone.start_after_milestone ? 'checked' : ''}>
                        <label class="form-check-label">Dynamic (starts when another milestone ends)</label>
                    </div>
                    <div class="dynamic-start-settings mt-2" style="display:${milestone.start_after_milestone ? 'block' : 'none'}">
                        <select class="form-select form-select-sm dynamic-start-target-select">
                            ${milestones.filter(m=>m.id!==milestone.id).map(m=>`<option value="${m.name}" ${m.name===milestone.start_after_milestone?'selected':''}>${m.name}</option>`).join('')}
                        </select>
                    </div>
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
                        <option value="">None</option>
                        <option value="Fixed Duration" ${milestone.disbursement_type === 'Fixed Duration' ? 'selected' : ''}>Fixed Duration</option>
                        <option value="Perpetuity" ${milestone.disbursement_type === 'Perpetuity' ? 'selected' : ''}>Perpetuity</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Amount${goalCheckbox('amount')}</label>
                    <div class="d-flex align-items-center amount-field">
                        <!-- FV radio + input -->
                        <div class="form-check form-check-inline me-1">
                            <input class="form-check-input amount-value-type" type="radio" name="amount_value_type_${milestone.id}" value="FV" ${milestone.amount_value_type !== 'PV' ? 'checked' : ''}>
                            <label class="form-check-label">FV</label>
                        </div>
                        <input type="number" class="form-control amount-fv-input me-2" style="max-width:120px" value="${fvVal}" ${milestone.amount_value_type === 'PV' ? 'disabled' : ''}>

                        <!-- PV radio + input -->
                        <div class="form-check form-check-inline me-1">
                            <input class="form-check-input amount-value-type" type="radio" name="amount_value_type_${milestone.id}" value="PV" ${milestone.amount_value_type === 'PV' ? 'checked' : ''}>
                            <label class="form-check-label">PV</label>
                        </div>
                        <input type="number" class="form-control amount-pv-input me-2" style="max-width:120px" value="${pvVal}" ${milestone.amount_value_type !== 'PV' ? 'disabled' : ''}>

                        ${scenarioControls('amount')}
                    </div>
                </div>
                <div class="mb-3 payment-field" style="display: ${['Asset', 'Liability'].includes(milestone.milestone_type) ? 'block' : 'none'}">
                    <label class="form-label">
                        Payment${goalCheckbox('payment')}
                        <span class="tooltip-container">
                            <i class="fas fa-info-circle info-icon"></i>
                            <span class="tooltip-text">Enter negative value for asset withdrawals / enter positive value for liability payments</span>
                        </span>
                    </label>
                    <div class="d-flex align-items-center">
                        <input type="number" class="form-control" name="payment" value="${paymentDisplay}">
                        ${scenarioControls('payment')}
                        <div class="form-check form-check-inline ms-2">
                            <input class="form-check-input payment-value-type" type="radio" name="payment_value_type_${milestone.id}" value="FV" ${milestone.payment_value_type !== 'PV' ? 'checked' : ''}>
                            <label class="form-check-label">FV</label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input payment-value-type" type="radio" name="payment_value_type_${milestone.id}" value="PV" ${milestone.payment_value_type === 'PV' ? 'checked' : ''}>
                            <label class="form-check-label">PV</label>
                        </div>
                    </div>
                </div>
                <div class="mb-3 annuity-fields" style="display: ${milestone.disbursement_type ? 'block' : 'none'}">
                    <label class="form-label">Occurrence${goalCheckbox('occurrence')}</label>
                    <select class="form-control" name="occurrence">
                        <option value="Monthly" ${milestone.occurrence === 'Monthly' ? 'selected' : ''}>Monthly</option>
                        <option value="Yearly" ${milestone.occurrence === 'Yearly' ? 'selected' : ''}>Yearly</option>
                    </select>
                    ${scenarioControls('occurrence')}
                </div>
                <div class="mb-3 annuity-fields duration-field" style="display: ${milestone.disbursement_type === 'Fixed Duration' ? 'block' : 'none'}">
                    <label class="form-label">Duration${goalCheckbox('duration')}</label>
                    <input type="number" class="form-control" name="duration" value="${milestone.duration || ''}" ${milestone.duration_end_at_milestone ? 'disabled' : ''}>
                    ${scenarioControls('duration')}

                    <!-- Dynamic duration toggle -->
                    <div class="form-check mt-2">
                        <input class="form-check-input dynamic-duration-checkbox" type="checkbox" ${milestone.duration_end_at_milestone ? 'checked' : ''}>
                        <label class="form-check-label">Dynamic (ends when another milestone starts)</label>
                    </div>
                    <div class="dynamic-duration-settings mt-2" style="display:${milestone.duration_end_at_milestone ? 'block' : 'none'}">
                        <select class="form-select form-select-sm dynamic-target-select">
                            ${milestones.filter(m=>m.id!==milestone.id).map(m=>`<option value="${m.name}" ${m.name===milestone.duration_end_at_milestone?'selected':''}>${m.name}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="mb-3 annuity-fields" style="display: ${milestone.disbursement_type ? 'block' : 'none'}">
                    <div class="d-flex justify-content-between align-items-center">
                        <label class="form-label mb-0">Rate of Return ($%)${goalCheckbox('rate_of_return')}</label>
                        <div class="d-flex align-items-center">
                            <button type="button" class="btn btn-sm btn-outline-primary me-2 add-curve-node" style="display:${milestone.rate_of_return_curve ? 'inline-block' : 'none'}">Add Node</button>
                            <button type="button" class="btn btn-sm btn-outline-danger me-2 delete-curve-node" style="display:${milestone.rate_of_return_curve ? 'inline-block' : 'none'}" disabled>Delete Node</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary toggle-curve-editor ms-2">${milestone.rate_of_return_curve ? 'Edit Curve' : 'Use Curve'}</button>
                        </div>
                    </div>
                    <input type="number" class="form-control mb-2" name="rate_of_return" value="${milestone.rate_of_return ? milestone.rate_of_return * 100 : ''}" step="0.1" ${milestone.rate_of_return_curve ? 'disabled' : ''}>
                    ${scenarioControls('rate_of_return')}
                    <div class="rate-curve-editor mt-2" style="display:${milestone.rate_of_return_curve ? 'block' : 'none'}">
                        <svg class="curve-canvas" width="100%" height="140" style="border:1px dashed #666; background:#000"></svg>
                        <input type="hidden" name="rate_of_return_curve" value='${milestone.rate_of_return_curve ? milestone.rate_of_return_curve : ''}'>
                        <div class="form-text">Drag nodes: X snaps to years, Y snaps to 0.1%. Click anywhere inside the chart to add a node. Right-click a node to remove it.</div>
                    </div>
                </div>
            </form>
            <div class="sub-milestones-container"></div>
        </div>
    `);
    
    console.log('Created form HTML:', form.prop('outerHTML'));
    
    // Add event listener for adding sub-milestone
    form.find('.add-sub-milestone').on('click', function() {
        addSubMilestone(form);
    });
    
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

    // Toggle curve editor
    form.find('.toggle-curve-editor').on('click', function() {
        const editor = form.find('.rate-curve-editor');
        const input = form.find('[name="rate_of_return"]');
        const hidden = form.find('[name="rate_of_return_curve"]');
        const svg = form.find('svg.curve-canvas');
        const addBtn = form.find('.add-curve-node');
        const delBtn = form.find('.delete-curve-node');
        const isShown = editor.is(':visible');
        if (isShown) {
            // Hide → disable curve
            editor.hide();
            hidden.val('');
            input.prop('disabled', false);
            addBtn.hide();
            delBtn.hide();
            $(this).text('Use Curve');
        } else {
            editor.show();
            input.prop('disabled', true);
            addBtn.show();
            delBtn.show();
            $(this).text('Edit Curve');
            initCurveEditor(svg.get(0), hidden, milestone);
        }
    });

    // Add Node button handler
    form.find('.add-curve-node').on('click', function() {
        const hidden = form.find('[name="rate_of_return_curve"]');
        let pts = [];
        try { pts = JSON.parse(hidden.val() || '[]'); } catch(e) { pts = []; }
        const maxYears = (milestone.duration && milestone.disbursement_type === 'Fixed Duration') ? milestone.duration : 30;
        pts.sort((a,b)=>a.x-b.x);
        const last = pts[pts.length-1] || { x: 0, y: (parseFloat(form.find('[name=\"rate_of_return\"]').val())||0)/100 };
        const nextX = Math.min(maxYears, (last.x || 0) + 1);
        const nextY = last.y || 0;
        if (!pts.some(p=>p.x===nextX)) {
            pts.push({ x: nextX, y: Math.round(nextY*10)/10 });
            hidden.val(JSON.stringify(pts));
            const svg = form.find('svg.curve-canvas');
            initCurveEditor(svg.get(0), hidden, milestone);
        }
    });

    // Initialize editor if curve present on load
    if (milestone.rate_of_return_curve) {
        const svg = form.find('svg.curve-canvas');
        const hidden = form.find('[name="rate_of_return_curve"]');
        initCurveEditor(svg.get(0), hidden, milestone);
    }
    
    // Add event listener for the editable header to update the milestone name on blur
    form.find('.editable-header').on('blur', function() {
        const newName = $(this).text().trim();
        const milestoneId = form.data('id');
        const milestone = milestones.find(m => m.id === milestoneId);
        if (milestone && newName !== milestone.name) {
            milestone.name = newName;
            $.ajax({
                url: `/api/milestones/${milestoneId}`,
                method: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify({ name: newName }),
                success: function(response) {
                    console.log('Milestone name updated:', response);
                },
                error: function(error) {
                    console.error('Error updating milestone name:', error);
                    alert('Error updating milestone name. Please try again.');
                }
            });
        }
    });
    
    // Add event listeners for scenario parameter controls
    form.on('click', '.add-scenario-value', function() {
        const param = $(this).data('param');
        let value;
        if (param === 'occurrence') {
            value = form.find('[name="occurrence"]').val();
        } else {
            value = form.find(`[name="${param}"]`).val();
        }
        if (value === '' || value === null || value === undefined) {
            return;
        }
        const milestoneId = form.data('id');
        $.ajax({
            url: `/api/milestones/${milestoneId}/scenario-values`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ parameter: param, value: parseFloat(value) || value }),
            success: function(updatedMilestone) {
                // Update local milestone data and refresh list
                const list = form.find(`.scenario-values-list[data-param="${param}"]`);
                if (list.find(`li span[data-value="${value}"]`).length === 0) {
                    list.append(`
                        <li><span class="dropdown-item d-flex justify-content-between align-items-center" data-value="${value}">
                            ${value}
                            <i class="fas fa-times text-danger delete-scenario-value" data-param="${param}" data-value="${value}"></i>
                        </span></li>`);
                }
                // Update global array
                const index = milestones.findIndex(m => m.id === milestoneId);
                if (index !== -1) {
                    milestones[index] = updatedMilestone;
                }

                // The scenario value should now be available for every related
                // milestone across all scenarios/sub-scenarios.  The simplest
                // way to guarantee the UI reflects this without re-implementing
                // the grouping logic in JavaScript is to reload the data.
                // A full page refresh will trigger the usual AJAX loaders that
                // repopulate the `milestones` array for the newly selected
                // scenario & sub-scenario selections.
                window.location.reload();
            },
            error: function(err) { console.error('Error adding scenario value', err); }
        });
    });

    form.on('click', '.delete-scenario-value', function(e) {
        e.stopPropagation();
        const param = $(this).data('param');
        const value = $(this).data('value');
        const milestoneId = form.data('id');
        const listItem = $(this).closest('li');
        $.ajax({
            url: `/api/milestones/${milestoneId}/scenario-values`,
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({ parameter: param, value: parseFloat(value) || value }),
            success: function(updatedMilestone) {
                listItem.remove();
                const index = milestones.findIndex(m => m.id === milestoneId);
                if (index !== -1) {
                    milestones[index] = updatedMilestone;
                }

                // Ensure UI stays in sync across all milestones after deletion.
                window.location.reload();
            },
            error: function(err) { console.error('Error deleting scenario value', err); }
        });
    });
    
    // After other listeners, add dynamic duration toggle handler
    form.find('.dynamic-duration-checkbox').on('change', function(){
        const wrapper = form.find('.dynamic-duration-settings');
        const durationInput = form.find('[name="duration"]');
        if(this.checked){
            wrapper.show();
            durationInput.prop('disabled', true);
        }else{
            wrapper.hide();
            durationInput.prop('disabled', false);
        }
    });
    
    // After start listener I add:
    form.find('.dynamic-start-checkbox').on('change', function(){
        const wrap = form.find('.dynamic-start-settings');
        const ageInput = form.find('.age-input');
        if(this.checked){
            wrap.show();
            ageInput.prop('disabled', true);
        } else {
            wrap.hide();
            ageInput.prop('disabled', false);
        }
    });

    // Helper to toggle enable/disable of PV / FV inputs
    function updateAmountEditability(frm) {
        const selected = frm.find('.amount-value-type:checked').val();
        frm.find('.amount-fv-input').prop('disabled', selected !== 'FV');
        frm.find('.amount-pv-input').prop('disabled', selected !== 'PV');
    }

    updateAmountEditability(form);
    form.on('change', '.amount-value-type', () => updateAmountEditability(form));
    
    return form;
}

function addSubMilestone(parentForm) {
    const parentId = parentForm.data('id');
    const parentMilestone = milestones.find(m => m.id === parentId);
    
    // Create new sub-milestone
    const subMilestone = {
        name: 'New Sub-Milestone',
        age_at_occurrence: parentMilestone.age_at_occurrence,
        milestone_type: 'Expense',
        disbursement_type: 'Fixed Duration',
        amount: 0,
        amount_value_type: 'FV',
        payment: null,
        payment_value_type: 'FV',
        occurrence: 'Yearly',
        duration: 1,
        rate_of_return: 0.0,
        order: milestones.length,
        parent_milestone_id: parentId,
        scenario_id: parseInt($('#scenarioSelect').val()) || 1,
        scenario_name: $('#scenarioSelect option:selected').text() || 'Base Scenario',
        sub_scenario_id: parseInt($('#subScenarioSelect').val()) || 1,
        sub_scenario_name: $('#subScenarioSelect option:selected').text() || 'Base Sub-Scenario'
    };
    
    $.ajax({
        url: '/api/milestones',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(subMilestone),
        success: function(response) {
            milestones.push(response);
            
            // If this is the first sub-milestone, create a parent milestone
            if (!parentMilestone.parent_milestone_id) {
                // Create a parent milestone
                $.ajax({
                    url: '/api/parent-milestones',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        name: parentMilestone.name,
                        min_age: parentMilestone.age_at_occurrence,
                        max_age: parentMilestone.age_at_occurrence
                    }),
                    success: function(parentResponse) {
                        // Update the parent milestone ID for both milestones
                        $.ajax({
                            url: `/api/milestones/${parentId}`,
                            method: 'PUT',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                parent_milestone_id: parentResponse.id
                            }),
                            success: function() {
                                $.ajax({
                                    url: `/api/milestones/${response.id}`,
                                    method: 'PUT',
                                    contentType: 'application/json',
                                    data: JSON.stringify({
                                        parent_milestone_id: parentResponse.id
                                    }),
                                    success: function() {
                                        // Refresh the page to show new structure
                                        window.location.reload();
                                    },
                                    error: function(error) {
                                        console.error('Error updating milestone:', error);
                                        alert('Error updating milestone. Please try again.');
                                    }
                                });
                            },
                            error: function(error) {
                                console.error('Error updating milestone:', error);
                                alert('Error updating milestone. Please try again.');
                            }
                        });
                    },
                    error: function(error) {
                        console.error('Error creating parent milestone:', error);
                        alert('Error creating parent milestone. Please try again.');
                    }
                });
            } else {
                // Just refresh the page to show the new sub-milestone
                window.location.reload();
            }
        },
        error: function(error) {
            console.error('Error creating sub-milestone:', error);
            alert('Error creating sub-milestone. Please try again.');
        }
    });
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
        };
        
        // Prevent manual amount updates for the system-managed Inheritance milestone
        if (milestone.name === 'Inheritance') {
            delete updatedMilestone.amount;
        }
        
        // Add payment field for Asset and Liability types
        if (['Asset', 'Liability'].includes(milestoneType)) {
            let paymentVal = parseFloat(form.find('[name="payment"]').val());
            if (isNaN(paymentVal)) paymentVal = null;
            let paymentType = form.find('.payment-value-type:checked').val() || 'FV';
            updatedMilestone.payment = paymentVal;
            updatedMilestone.payment_value_type = paymentType;
        }
        
        const dynCheckboxActive = form.find('.dynamic-duration-checkbox').is(':checked');
        const startDynActive = form.find('.dynamic-start-checkbox').is(':checked');

        if (dynCheckboxActive) {
            // Keep the stored numeric duration as a fallback for cycles; only
            // send the dynamic link.
            updatedMilestone.duration_end_at_milestone = form.find('.dynamic-target-select').val();
        } else {
            updatedMilestone.duration_end_at_milestone = null;
            updatedMilestone.duration = parseInt(form.find('[name="duration"]').val());
        }
        
        if (disbursementType) {
            updatedMilestone.occurrence = form.find('[name="occurrence"]').val();
            const curveVal = form.find('[name="rate_of_return_curve"]').val();
            if (curveVal && curveVal.length) {
                updatedMilestone.rate_of_return = null;
                updatedMilestone.rate_of_return_curve = curveVal;
            } else {
                updatedMilestone.rate_of_return = parseFloat(form.find('[name="rate_of_return"]').val()) / 100;
                updatedMilestone.rate_of_return_curve = null;
            }
            
            if (!dynCheckboxActive && disbursementType === 'Fixed Duration') {
                updatedMilestone.duration = parseInt(form.find('[name="duration"]').val());
            }
        } else {
            updatedMilestone.occurrence = null;
            updatedMilestone.duration = null;
            updatedMilestone.rate_of_return = null;
            updatedMilestone.rate_of_return_curve = null;
        }
        
        // After computing updatedMilestone fields, collect goal parameters
        const goalParameters = [];
        form.find('.goal-checkbox:checked').each(function() {
            goalParameters.push($(this).data('param'));
        });
        updatedMilestone.goal_parameters = goalParameters;
        
        if (startDynActive){
            // Preserve stored age; only transmit the dynamic reference.
            updatedMilestone.start_after_milestone = form.find('.dynamic-start-target-select').val();
        } else {
            updatedMilestone.age_at_occurrence = parseInt(form.find('[name="age_at_occurrence"]').val());
            updatedMilestone.start_after_milestone = null;
        }
        
        let amountType = form.find('.amount-value-type:checked').val() || 'FV';
        let amountValRaw = amountType === 'FV'
            ? parseFloat(form.find('.amount-fv-input').val())
            : parseFloat(form.find('.amount-pv-input').val());

        updatedMilestone.amount = amountValRaw;
        updatedMilestone.amount_value_type = amountType;
        // Leave PV numbers unconverted; backend will convert to FV upon save
        
        $.ajax({
            url: `/api/milestones/${milestoneId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(updatedMilestone),
            success: function(response) {
                Object.assign(milestone, response);
                updateTimeline();

                // Automatically persist the current scenario, then reload.
                if (window.scenarioManager && typeof window.scenarioManager.saveCurrentScenario === 'function') {
                    window.scenarioManager.saveCurrentScenario()
                        .catch(err => console.warn('Auto-saving scenario failed', err))
                        .finally(() => window.location.reload());
                } else {
                    window.location.reload();
                }
            },
            error: function(error) {
                console.error('Error updating milestone:', error);
                alert('Error updating milestone. Please try again.');
            }
        });
    }
}

// Curve editor implementation
function initCurveEditor(svgEl, hiddenInput, milestone) {
    if (!svgEl) return;
    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();
    const width = (svgEl.clientWidth && svgEl.clientWidth > 0) ? svgEl.clientWidth : 600;
    const height = (svgEl.clientHeight && svgEl.clientHeight > 0) ? svgEl.clientHeight : 140;

    const maxYears = (milestone && milestone.duration && milestone.disbursement_type === 'Fixed Duration') ? milestone.duration : 30;

    const margin = { left: 40, right: 10, top: 10, bottom: 24 };
    const x = d3.scaleLinear().domain([0, maxYears]).range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain([0, 0.2]).range([height - margin.bottom, margin.top]);

    const xAxis = (g) => g.attr('transform', `translate(0, ${height - margin.bottom})`).call(d3.axisBottom(x).ticks(maxYears).tickFormat(d=>d)).call(s=>s.selectAll('text').attr('fill','#ccc')).call(s=>s.selectAll('line,path').attr('stroke','#666'));
    const yAxis = (g) => g.attr('transform', `translate(${margin.left}, 0)`).call(d3.axisLeft(y).ticks(10).tickFormat(d=>`${(d*100).toFixed(0)}%`)).call(s=>s.selectAll('text').attr('fill','#ccc')).call(s=>s.selectAll('line,path').attr('stroke','#666'));

    svg.append('g').attr('class','x-axis').call(xAxis);
    svg.append('g').attr('class','y-axis').call(yAxis);

    // Vertical grid lines
    svg.append('g').attr('stroke', '#333')
        .selectAll('line.h').data(d3.range(0, maxYears+1)).enter()
        .append('line').attr('x1', d => x(d)).attr('y1', margin.top)
        .attr('x2', d => x(d)).attr('y2', height - margin.bottom);

    let points = [];
    try { points = JSON.parse(hiddenInput.val() || '[]'); } catch(e) { points = []; }
    if (!Array.isArray(points) || points.length === 0) {
        const basePct = parseFloat($(svgEl).closest('.annuity-fields').find('[name="rate_of_return"]').val());
        const baseDec = isNaN(basePct) ? 0.0 : (basePct/100);
        points = [{ x: 0, y: baseDec }];
    }

    function clampPts() {
        points = points.map(p=>({ x: Math.max(0, Math.min(maxYears, Math.round(p.x))), y: Math.max(0, Math.min(0.2, Math.round(p.y*10)/10)) }));
        points.sort((a,b)=>a.x-b.x);
    }
    clampPts();

    const line = d3.line()
        .x(d => x(d.x))
        .y(d => y(d.y))
        .curve(d3.curveStepAfter);

    const path = svg.append('path').attr('fill','none').attr('stroke','#4cc3ff').attr('stroke-width',2);
    const baseline = svg.append('path').attr('fill','none').attr('stroke','#888').attr('stroke-dasharray','4,4').attr('stroke-width',1.5);
    const segments = svg.append('g').attr('class','segments');

    function save() { hiddenInput.val(JSON.stringify(points)); }

    let selectedIndex = -1; // currently selected node index

    function render() {
        clampPts();
        path.attr('d', line(points));
        // Draw piecewise-constant segments extending to next node or end
        segments.selectAll('*').remove();
        for (let i = 0; i < points.length; i++) {
            const x0 = points[i].x;
            const y0 = points[i].y;
            const x1 = (i < points.length - 1) ? points[i+1].x : maxYears;
            const segPts = [{ x: x0, y: y0 }, { x: x1, y: y0 }];
            segments.append('path')
                .attr('fill','none')
                .attr('stroke','#4cc3ff')
                .attr('stroke-width',2)
                .attr('d', line(segPts));
        }
        // Baseline from leftmost node to right edge at that node's Y
        if (points.length) {
            const left = points[0];
            const blPoints = [{ x: left.x, y: left.y }, { x: maxYears, y: left.y }];
            baseline.attr('d', line(blPoints));
        }
        const nodes = svg.selectAll('circle.node').data(points, d=>d.x);
        nodes.enter().append('circle')
            .attr('class','node')
            .attr('r',5)
            .attr('fill','#4cc3ff')
            .style('cursor','pointer')
            .call(d3.drag()
                .on('drag', function(event, d){
                    const xi = Math.round(x.invert(event.x));
                    const yi = Math.round((y.invert(event.y))*10)/10; // 0.1 increments
                    d.x = Math.max(0, Math.min(maxYears, xi));
                    d.y = Math.max(0, Math.min(0.2, yi));
                    render();
                    save();
                })
            )
            .on('click', function(event, d){
                const idx = points.findIndex(p => p.x === d.x && p.y === d.y);
                selectedIndex = (selectedIndex === idx) ? -1 : idx;
                svg.selectAll('circle.node')
                   .attr('stroke', (n,i)=> i===selectedIndex ? '#fff' : 'none')
                   .attr('stroke-width', (n,i)=> i===selectedIndex ? 2 : 0);
                const delBtn = $(svgEl).closest('.annuity-fields').find('.delete-curve-node');
                delBtn.prop('disabled', !(selectedIndex >= 0 && points.length > 1));
            })
            .merge(nodes)
            .attr('cx', d=>x(d.x))
            .attr('cy', d=>y(d.y));
        nodes.exit().remove();
    }

    svg.on('click', function(event){
        const [px, py] = d3.pointer(event);
        const xi = Math.round(x.invert(px));
        const yi = Math.round((y.invert(py))*10)/10;
        if (xi < 0 || xi > maxYears) return;
        if (!points.some(p=>p.x===xi)) {
            points.push({ x: xi, y: Math.max(0, Math.min(0.2, yi)) });
            render();
            save();
        }
    });

    render();

    // Delete selected node button
    const delBtn = $(svgEl).closest('.annuity-fields').find('.delete-curve-node');
    delBtn.off('click.roi').on('click.roi', function(){
        if (selectedIndex >= 0 && points.length > 1) {
            points.splice(selectedIndex, 1);
            selectedIndex = -1;
            render();
            save();
            $(this).prop('disabled', true);
        }
    });
}
function handleMilestoneDelete(e) {
    const form = $(e.target).closest('.milestone-form, .sub-milestone-form');
    const milestoneId = form.data('id');
    const milestone = milestones.find(m => m.id === milestoneId);
    
    // Check if this is a sub-milestone
    if (milestone.parent_milestone_id) {
        // Get the parent milestone
        const parentId = milestone.parent_milestone_id;
        const parentMilestone = milestones.find(m => m.id === parentId);
        
        // Get all sub-milestones for this parent
        const subMilestones = milestones.filter(m => m.parent_milestone_id === parentId);
        
        // If this is the last sub-milestone, convert parent back to a regular milestone
        if (subMilestones.length === 1) {
            // Delete the sub-milestone
            $.ajax({
                url: `/api/milestones/${milestoneId}`,
                method: 'DELETE',
                success: function() {
                    // Remove the milestone from the local array
                    milestones = milestones.filter(m => m.id !== milestoneId);
                    // Refresh the page to show new structure
                    window.location.reload();
                },
                error: function(error) {
                    console.error('Error deleting milestone:', error);
                    alert('Error deleting milestone. Please try again.');
                }
            });
        } else {
            // Just delete the sub-milestone
            $.ajax({
                url: `/api/milestones/${milestoneId}`,
                method: 'DELETE',
                success: function() {
                    // Remove the milestone from the local array
                    milestones = milestones.filter(m => m.id !== milestoneId);
                    // Refresh the page to show new structure
                    window.location.reload();
                },
                error: function(error) {
                    console.error('Error deleting milestone:', error);
                    alert('Error deleting milestone. Please try again.');
                }
            });
        }
    } else {
        // This is a parent milestone, check if it has sub-milestones
        const subMilestones = milestones.filter(m => m.parent_milestone_id === milestoneId);
        
        if (subMilestones.length > 0) {
            // Delete all sub-milestones first
            const deletePromises = subMilestones.map(subMilestone => {
                return $.ajax({
                    url: `/api/milestones/${subMilestone.id}`,
                    method: 'DELETE'
                });
            });
            
            Promise.all(deletePromises)
                .then(() => {
                    // Then delete the parent milestone
                    return $.ajax({
                        url: `/api/milestones/${milestoneId}`,
                        method: 'DELETE'
                    });
                })
                .then(() => {
                    // Remove all related milestones from the local array
                    milestones = milestones.filter(m => m.id !== milestoneId && m.parent_milestone_id !== milestoneId);
                    // Refresh the page to show new structure
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error deleting milestones:', error);
                    alert('Error deleting milestones. Please try again.');
                });
        } else {
            // Just delete the milestone
            $.ajax({
                url: `/api/milestones/${milestoneId}`,
                method: 'DELETE',
                success: function() {
                    // Remove the milestone from the local array
                    milestones = milestones.filter(m => m.id !== milestoneId);
                    // Refresh the page to show new structure
                    window.location.reload();
                },
                error: function(error) {
                    console.error('Error deleting milestone:', error);
                    alert('Error deleting milestone. Please try again.');
                }
            });
        }
    }
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

function updateCharts() {
    // Update net worth chart
    fetch('/api/net-worth-range')
        .then(response => response.json())
        .then(rangeData => {
            console.log('Net worth range:', rangeData);
            if (window.netWorthChart && typeof window.netWorthChart.setRangeData === 'function') {
                window.netWorthChart.setRangeData(rangeData);
            }

            // Load default line (scenario_id=1, sub_scenario_id=1) only once per page load
            if (!window._defaultLineLoaded) {
                fetch('/api/net-worth-line?scenario_id=1&sub_scenario_id=1')
                    .then(r=>r.json())
                    .then(lineData => {
                        if (window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                            window.netWorthChart.setLineData(lineData);
                        }
                        // Load Monte Carlo band for default selection
                        fetch('/api/net-worth-mc-range?scenario_id=1&sub_scenario_id=1')
                            .then(r=>r.json())
                            .then(rangeData=>{
                                if(window.netWorthChart && typeof window.netWorthChart.setMcRangeData==='function'){
                                    window.netWorthChart.setMcRangeData(rangeData);
                                }
                                window.lastClickedMcRangeData = rangeData;
                            })
                            .catch(err=>console.error('Error fetching default MC range',err));
                        // Expose for scenario_table preview reverts
                        window.lastClickedLineData = lineData;
                        window._defaultLineLoaded = true;
                    })
                    .catch(err => console.error('Error fetching default net worth line', err));
            }

            // If the range is empty, fall back to a simple line from /api/net-worth
            if ((!rangeData || rangeData.length === 0) && window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                fetch('/api/net-worth')
                    .then(r => r.json())
                    .then(lineData => window.netWorthChart.setLineData(lineData))
                    .catch(err => console.error('Error fetching fallback net worth line:', err));
            }
        })
        .catch(error => {
            console.error('Error fetching net worth range:', error);
            // Fallback straight away on error
            fetch('/api/net-worth')
                .then(r => r.json())
                .then(lineData => {
                    if (window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                        window.netWorthChart.setLineData(lineData);
                    }
                })
                .catch(err2 => console.error('Error fetching fallback net worth line:', err2));
        });

    // Fetch liquidity data
    fetch('/api/liquidity')
        .then(response => response.json())
        .then(data => {
            console.log('Liquidity data received:', data);
            if (window.liquidityChart) {
                console.log('Updating liquidity chart with data');
                window.liquidityChart.updateChart(data);
            } else {
                console.error('Liquidity chart not initialized');
            }
        })
        .catch(error => console.error('Error fetching liquidity data:', error));
}

// Initial chart update
// document.addEventListener('DOMContentLoaded', () => {
//     console.log('DOM loaded, initializing charts');
//     updateCharts();
// }); 