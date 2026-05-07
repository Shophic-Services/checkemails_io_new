$(function () {
    const $email = $('#emailInput');
    const $btn = $('#checkBtn');
    const $result = $('#resultContainer');
    const $analysisresult = $('#analysisResultContainer');
    const $pagesize = $('select#pageSize');
    const $inputsearch = $('input#searchInput');
    const $errormessage = $('.error-message');
    const $errormessageclose = $('.error-message-close');
    const EMAIL_TYPE = {
        8: {
            label: 'Professional',
            badge: 'bg-blue-100 text-blue-800',
            desc: "The domain name is used for professional email services."
        },
        9: {
            label: 'Webmail',
            badge: 'bg-cyan-100 text-cyan-800',
            desc: 'This is a webmail email address. This domain name is used to create personal email addresses.'
        },
        7: {
            label: 'Disposable',
            badge: 'bg-red-100 text-red-800',
            desc: 'This is a disposable or temporary email address.'
        },
        5: {
            label: 'Unknown',
            badge: 'bg-gray-100 text-gray-800',
            desc: 'Email type could not be confidently determined.'
        }
    };
    const defaultPageSize = 10;
    let currentPage = 1; // Current page
    let pageSize = defaultPageSize; // Page size
    let searchQuery = ""; // Search query
    let sortField = ""; // Field to sort by
    let sortOrder = "asc"; // Sort order (asc or desc)

    var csrftoken = $("[name=csrfmiddlewaretoken]").val();
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    /* Email regex */
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    // Function to fetch and render data
    function fetchData() {
        $.ajax({
            url: `/api/single-validation-history/?page=${currentPage}&page_size=${pageSize}`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                search: searchQuery,
                // sort_field: sortField,
                // sort_order: sortOrder,
            }),
            success: function (res) {
                response = res.response;
                renderTable(response.results);   // DRF default
                updatePagination({
                    count: response.count,
                    next: response.next,
                    previous: response.previous,
                    current: response.current,
                    total_pages: response.total_pages,
                });
                $('.entries-info').text(`Showing 1 to ${response.results.length} of ${response.count} entries`);
            },
            error: function (xhr) {
                console.error("Error fetching data:", xhr.responseText);
            },
        });
    }
    function emailResultBadge(result) {
        const base = "inline-block px-2 py-1 rounded text-base font-bold ";
    
        if (!result) {
            return `<span class="${base} bg-gray-100 text-gray-700">-</span>`;
        }
        if (result.includes("Unable to Confirm")) {
            return `<span class="${base} bg-gray-100 text-gray-700">${result}</span>`;
        }
        if (result.includes("Do Not Send")) {
            return `<span class="${base} bg-red-100 text-red-700">${result}</span>`;
        }
        if (result.includes("Safe to Send")) {
            return `<span class="${base} bg-green-100 text-green-700">${result}</span>`;
        }
        if (result.includes("Risky")) {
            return `<span class="${base} bg-orange-100 text-orange-700">${result}</span>`;
        }
    
        return `<span class="${base} bg-gray-100 text-gray-700">${result}</span>`;
    }
    // Function to render table rows
    function renderTable(data) {
        const tbody = $("table tbody");
        tbody.empty();
        if (data.length === 0) {
            tbody.append('<tr><td colspan="7" class="text-center">No data found</td></tr>');
        } else {
            data.forEach((item) => {
                tbody.append(`
                    <tr class="border-b border-gray-100 hover:bg-gray-50 text-lg">
                        <td class="py-4 px-2 text-gray-500 font-bold">${item.email}</td>
                        <td class="py-4 px-2 text-gray-500 font-bold">${emailResultBadge(item.result)}</td>
                        
                        <td class="py-4 px-2 text-center">
                            <div class="flex justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-x ${
                                    item.catch_all ? "text-yellow-400" : "text-gray-300"
                                } fill-current bg-white rounded-full" aria-hidden="true">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <path d="m15 9-6 6"></path>
                                    <path d="m9 9 6 6"></path>
                                </svg>
                            </div>
                        </td>
                        <td class="py-4 px-2 text-center">
                            <span class="inline-block px-2 py-1 rounded text-base font-bold ${
                                item.status === "Disposable"
                                    ? "bg-red-100 text-red-700"
                                    : item.status === "Professional"
                                    ? "bg-blue-100 text-blue-700"
                                    : item.status === "Webmail"
                                    ? "bg-cyan-100 text-cyan-700"
                                    : item.status === "Risky"
                                    ? "bg-orange-100 text-orange-700"
                                    : "bg-gray-100 text-gray-700"
                            }">${item.status}</span>
                        </td>
                        <td class="py-4 px-2 text-center">
                            <div class="flex justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-x ${
                                    item.domain ? "text-green-400" : "text-gray-300"
                                } fill-current bg-white rounded-full" aria-hidden="true">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <path d="m15 9-6 6"></path>
                                    <path d="m9 9 6 6"></path>
                                </svg>
                            </div>
                        </td>
                        <td class="py-4 px-2 text-center">
                            <div class="flex justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-x ${
                                    item.role_based ? "text-green-400" : "text-gray-300"
                                } fill-current bg-white rounded-full" aria-hidden="true">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <path d="m15 9-6 6"></path>
                                    <path d="m9 9 6 6"></path>
                                </svg>
                            </div>
                        </td>
                        <td class="py-4 px-2 text-center">
                            <div class="flex justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-x ${
                                    item.disposable ? "text-green-400" : "text-gray-300"
                                } fill-current bg-white rounded-full" aria-hidden="true">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <path d="m15 9-6 6"></path>
                                    <path d="m9 9 6 6"></path>
                                </svg>
                            </div>
                        </td>
                        <td class="py-4 px-2 text-left text-gray-500">${item.create_date}</td>
                    </tr>
                `);
            });
        }
    }

    function updatePagination(pagination) {
        const paginationContainer = $(".pagination");
        paginationContainer.empty();

        if (pagination.previous) {
            paginationContainer.append(
                `<span class="px-3 py-1.5 border-r border-gray-300 hover:bg-gray-100 previous-page cursor-pointer" data-page="${pagination.current_page - 1}">Previous</span>`
            );
        }
        else{
            paginationContainer.append(
                `<span class="px-3 py-1.5 border-r border-gray-300 text-gray-400 cursor-not-allowed">Previous</span>`
            );
        }

        for (let i = 1; i <= pagination.total_pages; i++) {
            paginationContainer.append(
                `<span class="px-3 py-1.5 current-page cursor-pointer ${
                    pagination.current === i ? "bg-primary text-white font-medium" : ""
                }" data-page="${i}">${i}</span>`
            );
        }

        if (pagination.next) {
            paginationContainer.append(
                `<span class="px-3 py-1.5 border-l border-gray-300 hover:bg-gray-100 next-page cursor-pointer" data-page="${pagination.current_page + 1}">Next</span>`
            );
        }
        else{
            paginationContainer.append(
                `<span class="px-3 py-1.5 border-l border-gray-300 text-gray-400 cursor-not-allowed">Next</span>`
            );
        }
    }

    $pagesize.on("change", function () {
        pageSize = $(this).val();
        currentPage = 1; // Reset to the first page
        fetchData();
    });

    $inputsearch.on("input", function () {
        searchQuery = $(this).val();
        currentPage = 1; // Reset to the first page
        fetchData();
    });

    $(document).on("click", ".pagination span.previous-page, .pagination span.current-page, .pagination span.next-page", function () {
        currentPage = $(this).data("page");
        fetchData();
    });

    /* Enable / disable button */
    $email.on('input', function () {
        const val = $(this).val().trim();
        $btn.prop('disabled', val.length <= 1);
    });
    $errormessageclose.on('click', function () {
        $errormessage.addClass('hidden');
    });
    /* Button click */
    $btn.on('click', function () {
        const email = $email.val().trim();
        $errormessage.addClass('hidden');
        $('.error-message-text').html('Please try again.');
        if (!isValidEmail(email)) {
            
            $errormessage.removeClass('hidden');
            $('.error-message-text').html('Enter a valid email address.');
            return;
        }

        startLoading();
        $.ajax({
            url: '/api/single-validation/',
            type: 'POST',
            data: { email },
            beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
                // Start 10 sec timer
                setTimeout(() => {
                    $result.html(`
            <div class="flex flex-col items-center animate-in zoom-in duration-700"><div class="relative mb-8"><div class="absolute inset-0 bg-primary/10 rounded-full scale-110 animate-ping"></div><div class="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center relative"><svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity text-primary animate-pulse" aria-hidden="true"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"></path></svg></div><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-shield absolute -bottom-1 -right-1 text-primary animate-bounce bg-white rounded-full p-1 shadow-sm" aria-hidden="true"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"></path></svg></div><h4 class="text-primary font-bold text-lg mb-2">Analyzing more deeply...</h4><p class="text-gray-500 text-base mb-8 leading-relaxed">The server is taking longer than usual. Performing a heavy digging to ensure more accuracy.</p></div>
        `);
                }, 7000);
            },
            success: function (res) {
                try {
                    if(res.status == 200){

                        renderResult(res);
                        const credit_balance = Number(res.response.credit_balance) || 0
                        const credit_reserved = Number(res.response.credit_reserved) || 0

                        if (res.response.credit_balance != null) {
                            $('.available-balance').text(credit_balance)
                            $('.credit-reserved').text(credit_reserved)
                            $('.credit-balance').text(credit_balance + credit_reserved)
                            searchQuery = ''
                            currentPage = 1
                        }
                        fetchData();
                        stopLoading();
                    }
                    else{
                        $errormessage.removeClass('hidden');
                        $('.error-message-text').html(res.message || 'Please try again.');
                        $analysisresult.removeClass('hidden');
                        $result.addClass('hidden');   
                        $btn.prop('disabled', false).text('Check');
                    }
                }
                catch (e) {
                    $errormessage.removeClass('hidden');
                    $('.error-message-text').html(res.message || 'Please try again.');
                    $analysisresult.removeClass('hidden');
                    $result.addClass('hidden'); 
                    $btn.prop('disabled', false).text('Check');
                }
            },
            error: function () {
                $errormessage.removeClass('hidden');
                $result.addClass('hidden');
                $result.html('');
                // $email.val('');
                $analysisresult.removeClass('hidden');
                $btn.prop('disabled', false).text('Check');
            },
            complete: function () {
                
            }
        });
    });

    /* Loading UI */
    function startLoading() {
        $btn.prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Checking...
        `);
        $analysisresult.addClass('hidden');
        $result.removeClass('hidden');
        $result.html(`
            <div class="flex flex-col items-center justify-center py-12 text-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle text-primary animate-spin mb-4" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
                <p class="text-base text-gray-600 font-medium">Analyzing email address...</p>
            </div>
        `);
    }

    function stopLoading() {
        $email.val('');
        $btn.prop('disabled', true).text('Check');
    }

    function gridItem(title, condition, yes, no, yesDesc, noDesc) {       
        return `
            <div>
                <div class="flex items-center gap-3 mb-2">
                    <h4 class="text-base text-gray-800 font-bold">${title}</h4>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        condition
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                    }">
                        ${condition ? yes : no}
                    </span>
                </div>
                <p class="text-gray-500 text-base leading-relaxed">
                    ${condition ? yesDesc : noDesc}
                </p>
            </div>
            `;     
        }
    
    function gridWaringItem(title, condition, yes, no, yesDesc, noDesc) {       
        return `
            <div>
                <div class="flex items-center gap-3 mb-2">
                    <h4 class="text-base text-gray-800 font-bold">${title}</h4>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        condition
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                    }">
                        ${condition ? yes : no}
                    </span>
                </div>
                <p class="text-gray-500 text-base leading-relaxed">
                    ${condition ? yesDesc : noDesc}
                </p>
            </div>
            `;     
        }

    function attribute(title, badge, label, desc) {
        return `
            <div>
                <div class="flex items-center gap-3 mb-2">
                    <h4 class="text-base text-gray-800 font-bold">${title}</h4>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        badge}">
                        ${label}
                    </span>
                </div>
                <p class="text-gray-500 text-base leading-relaxed">
                    ${desc}
                </p>
            </div>
            `;
    }
    
    const EMAIL_RESULT_UI_MESSAGE_MAP = {
    'Safe to Send - Deliverable': 'This email address can be used safely.',
    'Risky - Use with Caution': 'This email address should be used with caution.',
    'Disposable': 'This email address should not be used.',
    'Do Not Send - Undeliverable': 'This email address may not be safe to use.',
    'Do Not Send - Unable to Confirm': 'This email address may not be safe to use.'
};
function getUiEmailMessage(emailResult) {
    return EMAIL_RESULT_UI_MESSAGE_MAP[emailResult]
        || 'This email address may not be safe to use.';
}
    /* Render result */
    function renderResult(api) {
        const r = api.response;
    
        const isValid = r.quality == 1;
        const email = r.email;
    
        let statusText = isValid ? 'Valid' : 'Invalid';
        let statusColor = isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700';
        let ringColor = isValid ? 'ring-green-100' : 'ring-red-100';
    
        const score = isValid ? 100 : 40;
        const statusscoreColor = isValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700';
        $result.removeClass('hidden');
        const type = EMAIL_TYPE[r.check.type.code] || EMAIL_TYPE[4];
        if (r.quality == 3){

        statusText = 'Risky';
        statusColor = 'bg-orange-100 text-orange-700';
        ringColor = 'ring-orange-100';
        }
        if (r.quality == 5){

        statusText = 'Unknown';
        statusColor = 'bg-gray-100 text-gray-700';
        ringColor = 'ring-gray-100'
        }
        if (r.quality == 7){

        statusText = 'Disposable';
        statusColor = 'bg-red-100 text-red-700';
        ringColor = 'ring-red-100'
        }
        
        $result.html(`
    <div class="animate-in fade-in slide-in-from-bottom-2 duration-500">
    
        <!-- HEADER -->
        <div class="flex flex-col sm:flex-row gap-6 border-b border-gray-100 pb-8 mb-8">
            <div class="w-20 h-20 rounded-full bg-gray-100 overflow-hidden shrink-0 ring-2 ring-offset-2 ${ringColor}">
                <img
                    src="https://ui-avatars.com/api/?name=${email[0]}${email[1]}&background=e0e7ff&color=3b82f6&bold=true"
                    alt="Avatar"
                    class="w-full h-full object-cover"
                />
            </div>
    
            <div class="flex-1">
                <div class="flex items-center flex-wrap gap-2 mb-1">
                    <h3 class="text-xl font-bold text-gray-800">${email}</h3>
                    <span class="text-gray-400 font-light">is</span>
                    <span class="px-1.5 py-0.5 rounded ${statusColor} font-bold">${statusText}</span>
                </div>
    
                <p class="text-gray-500 text-base mb-3">
                    ${getUiEmailMessage(r.result)}
                </p>
    
                <div class="flex items-center gap-4">
                    <span class="${statusscoreColor} font-bold px-3 py-1 rounded text-base flex items-center shadow-sm hidden">
                        ${score}% Safe
                    </span>
                    <button class="text-gray-400 text-base hover:text-gray-600 hover:underline hidden">
                        Hide details
                    </button>
                </div>
            </div>
        </div>
    
        <!-- GRID -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-8 mb-8">
    
            ${gridWaringItem(
                'Catch all',
                r.check.catch_all.valid,
                'Detected',
                'Not Detected',
                'The server accepts all emails.',
                'The domain is not set to catch all non-existent emails.'
            )}
            
            ${attribute(
                'Type',
                type.badge,
                type.label,
                type.desc,
                ''
            )}
    
            ${gridItem(
                'Domain Status',
                r.check.domain.valid,
                'Valid',
                'Invalid',
                'The domain name exists and has valid MX records.',
                'The domain name does not exist or has invalid MX records.'
            )}
    
            ${gridWaringItem(
                'Role Based',
                r.check.role_based.valid,
                'Detected',
                'Not Detected',
                'This is a role-based email address.',
                'This email address is not role-based.'
            )}
    
        </div>
    </div>
    `);
    }
    
    

});