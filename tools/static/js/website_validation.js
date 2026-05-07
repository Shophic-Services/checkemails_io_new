const PREVIEW_LIMIT = 50;
const WEBSITE_REGEX = /^[a-z0-9.-]+\.[a-z]{2,}$/i;
let websiteSocket;
let selectedWebsiteColumns = new Set();
const RADIUS = 90;
let deleteUUID = null;

let selectedFile = null;
let currentPage = 1; // Current page
let currentStatus = 'ALL'
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const CHECK_ICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"
     viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="4" stroke-linecap="round" stroke-linejoin="round"
     class="text-primary">
    <path d="M20 6 9 17l-5-5"></path>
</svg>`;
let websitePollingInterval = null;
const POLL_INTERVAL = 1500 //5 * 60 * 1000; // 5 minutes
const INPROGRESS = 3;
const COMPLETED = 5;
const ERROR = 4;

const STATUS = {
    READY: 1,
    PROCESSING: 3,
    COMPLETED: 5,
    FAILED: 4,
};


$(document).ready(function () {
    initWebsiteSocket();
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
    // Open Modal
    $('#openUploadModal').on('click', function () {
      $('#uploadModal').removeClass('hidden');
    });

    // Close Modal (X)
    $('.upload-close-modal').on('click', function () {
      $('#uploadModal').addClass('hidden');
      $('#fileTrigger')
        .addClass('text-gray-400')
        .removeClass('text-gray-900 font-medium')
        .text('Choose List');
        $('#fileInput').val('')
        selectedFile = null
    });

    // // Close on background click
    $('#uploadModal').on('click', function (e) {
      if ($(e.target).is('#uploadModal')) {
        $('#uploadModal').addClass('hidden');
        $('#fileTrigger')
        .addClass('text-gray-400')
        .removeClass('text-gray-900 font-medium')
        .text('Choose List');
        $('#fileInput').val('')
        selectedFile = null
      }
    });


  // Trigger hidden file input
  $('#fileTrigger').on('click', function () {
    $('#fileInput').click();
  });

  $('input[name="website_first_row_label"]').on('change', function () {
    if ($(this).is(':checked') && this.value === 'yes') {
        $('.header-row-strike').addClass('italic line-through text-gray-300');
        $('.header-row-strike').removeClass('text-gray-500 font-medium');
    } else {
        $('.header-row-strike').removeClass('italic line-through text-gray-300');
        $('.header-row-strike').addClass('text-gray-500 font-medium');

    }
});

  // Handle file selection
  $('#fileInput').on('change', function (e) {
    const file = e.target.files[0];

    if (file) {
      selectedFile = file;

      // Update UI
      $('#fileTrigger')
        .removeClass('text-gray-400')
        .addClass('text-gray-900 font-medium')
        .text(file.name);

      // Clear error
      $('#uploadError').addClass('hidden');
    }
  });

  // Handle upload submit
  $(document).on('click', '#submitUpload' ,function () {

    $('#uploadError').addClass('hidden');
    if (!selectedFile) {
      showError('Please select a file to continue.');
      return;
    }

    const fileName = selectedFile.name.toLowerCase();
    const isCsv = fileName.endsWith('.csv');
    const isXlsx = fileName.endsWith('.xlsx');
    
    $('.upload-file-name').text(fileName);

    if (!isCsv && !isXlsx) {
      showError('Please upload a .CSV or .XLSX file only.');
      return;
    }

    $('#submitUpload').prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Checking...
        `);

    const reader = new FileReader();

    reader.onload = function (evt) {
        const data = new Uint8Array(evt.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
    
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
    
        // Object-based rows
        const sheetData = XLSX.utils.sheet_to_json(worksheet, {
            header: 1,
            defval: '',
            raw: false
        });
    
        if (!sheetData.length) {
            $('#excelPreview').html(
                '<p class="p-4 text-base text-gray-500">No data found</p>'
            );
            return;
        }
    
        const headers = sheetData[0].map((h, i) =>
            h ? h.toString().trim() : `Column ${i + 1}`
        );
    
        const rowValues = sheetData.slice(1);
    
        // Detect website columns
        const websiteColumns = detectWebsiteColumns(headers, rowValues);
    
        $('#websiteColumns').text(
            websiteColumns.length ? websiteColumns.join(', ') : 'None'
        );

        if (!websiteColumns.length) {
            showError('File doesnot contains any websites.');
            $('#submitUpload').prop('disabled', false).html(`
                Submit
            `);
            return;
        }
        $('#uploadError').addClass('hidden');
        $('#uploadModal').addClass('hidden');
        $('#listDiv').addClass('hidden');
        $('#statusDiv').addClass('hidden');
        $('#headingDiv').addClass('hidden');
        $('#listDivEmpty').addClass('hidden');
        $('#previewState').removeClass('hidden');
        renderPreview(headers, rowValues, 5);
        updateHeaderUI();
        updateHiddenInput();
    };
    reader.readAsArrayBuffer(selectedFile);
  });
//   $(document).on('click', '.column-selector', function () {
//     const index = $(this).data('index');

//     if (selectedWebsiteColumns.has(index)) {
//         selectedWebsiteColumns.delete(index);
//     } else {
//         selectedWebsiteColumns.add(index);
//     }

//     updateHeaderUI();
//     updateHiddenInput();
//     // $('#selected_website_column').val([...selectedWebsiteColumns].join(','));
// });
$(document).on("click", '.verification-list', function () {
    const selectedId = $(this).data('id');
    $('.verification-list-stats').addClass('hidden')
    $('.verification-list').removeClass('border-primary ring-1 ring-primary shadow-md').addClass('border-border hover:border-blue-200 hover:shadow-md')
    $(this).removeClass('border-border hover:border-blue-200 hover:shadow-md').addClass('border-primary ring-1 ring-primary shadow-md')
    $('.verification-list-stats[data-id="' + selectedId + '"]').removeClass('hidden')
    updateArrowPosition(selectedId);
    $('.custom-scrollbar').on('scroll', function () {
        if (selectedId !== null) {
            updateArrowPosition(selectedId);
        }
        });
})
$(document).on("click", ".pagination span.previous-page, .pagination span.current-page, .pagination span.next-page", function () {
        currentPage = $(this).data("page");
        fetchData();
    });

$(document).on("click", ".status-tab[data-status]", function () {
    currentStatus = $(this).data("status");

    // reset all tabs
    $(".status-tab")
        .removeClass("text-primary border-b-2 border-primary")
        .addClass("text-gray-400 hover:text-gray-600");

    // activate clicked tab
    $(this)
        .removeClass("text-gray-400 hover:text-gray-600")
        .addClass("text-primary border-b-2 border-primary");

    currentPage = 1;
    fetchData();
});

  $(document).on('click', '.delete-list',function () {
    deleteUUID = $(this).data('id');
    const fileName = $(this).data('filename');

    $('#confirmFileName').text(fileName);
    $('#confirmUUID').text(deleteUUID);

    $('#ConfirmModal').removeClass('hidden');
  })
  $('#confirmDeleteYes').on('click', function () {
    $('#confirmDeleteYes').prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin mr-2" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Deleting...
        `);
    if (!deleteUUID) return;

    $.ajax({
        url: `/api/website-validation/${deleteUUID}/delete/`,
        type: 'DELETE',
        success: function () {
            location.reload();
        },
        error: function () {
            $('#confirmDeleteYes').prop('disabled', false).html(`
           Yes, Delete
        `);
        }
    });
});
$(document).on('click', '.delete-close-modal', function () {
    $('#ConfirmModal').addClass('hidden');
    deleteUUID = null;
});

  $(document).on('click', '.initiate-extraction',function () {
    $(this).prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin mr-3" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Initiating...
        `);
        $cardStats = $(this).closest('.verification-list-stats')
    upload_session_path = $cardStats.attr('data-id')
    $cardStats.find('.delete-list').addClass('hidden')
$.ajax({
            url: '/ajax/initiate-extraction/',
            type: 'POST',
            data: { upload_session_path },
            success: function (res) {
                try {
                    if(res.status == 200){

                        $cardStats.find('.start-verification-div').addClass('hidden')
                        $cardStats.find('.ongoing-verification-div').removeClass('hidden')
                        $cardStats.find('.stats-status-failed-div').addClass('hidden');
                        $cardStats.find('.list-chart').removeClass('hidden')
                        updateListStatus(upload_session_path, STATUS.PROCESSING);
                        updateProgress(upload_session_path, 0, 0);
                        const credit_balance = Number(res.credit_balance) || 0
                        const credit_reserved = Number(res.credit_reserved) || 0

                        if (res.credit_balance != null) {
                            $('.available-balance').text(credit_balance)
                            $('.credit-reserved').text(credit_reserved)
                            $('.credit-balance').text(credit_balance + credit_reserved)
                        }
                    }
                    else{
                    updateListStatus(upload_session_path, STATUS.FAILED)
                        $cardStats.find('.start-verification-div').addClass('hidden')
                        $cardStats.find('.ongoing-verification-div').removeClass('hidden')
                        $cardStats.find('.stats-status-failed-div').removeClass('hidden');
                        updateStatsStatus(upload_session_path, STATUS.FAILED)
                    }
                }
                catch (e) {
                    updateListStatus(upload_session_path, STATUS.FAILED)
                        $cardStats.find('.start-verification-div').addClass('hidden')
                        $cardStats.find('.ongoing-verification-div').removeClass('hidden')
                    $cardStats.find('.stats-status-failed-div').removeClass('hidden');
                        updateStatsStatus(upload_session_path, STATUS.FAILED)
                }
            },
            error: function () {
                    updateListStatus(upload_session_path, STATUS.FAILED)
                        $cardStats.find('.start-verification-div').addClass('hidden')
                        $cardStats.find('.ongoing-verification-div').removeClass('hidden')
                $cardStats.find('.stats-status-failed-div').removeClass('hidden');
                        updateStatsStatus(upload_session_path, STATUS.FAILED)
            },
            complete: function () {
                
            }
        });
    });
  
  // Handle upload submit
  $('.validate-websites').on('click', function () {
    $('.upload-message-text').text('Uploading and Preparing your List...');
    $('.upload-message-div').text('We have queued your list and it will be prepared shortly for validation. You can leave this window and it will redirect you to active lists once analyzing has been finished.');
    $('.error-class').removeClass('text-red-500');
    $('.progress-info.error-class').text('0%');
    $('.progress-bar').css('width', '0%');
    $('.tracking-wider.error-class').text('Analysis Progress');
    $('.error-class-progress').removeClass('bg-red-50 border-red-100');
    $('.error-class-progress .error-bar').removeClass('bg-red-500');
    $('.processing-error-div').addClass('hidden');
    $('.processing-div').removeClass('hidden')
    $('.lucide-search').removeClass('text-red-600')
    $('#listDiv').addClass('hidden');
    $('#statusDiv').addClass('hidden');
    $('#headingDiv').addClass('hidden');
    $('#preparingState').removeClass('hidden');
    $('#previewState').addClass('hidden');
    setTimeout(function () {
    $('#uploadError').addClass('hidden');
    $('#uploadModal').addClass('hidden');
    setTimeout(function () {
        new ChunkUploader().start();
      }, 1000);
    }, 1500);
  });
  let selectedId = $('.verification-list').first().data('id');
  updateArrowPosition(selectedId)
  $('.custom-scrollbar').on('scroll', function () {
    if (selectedId !== null) {
        updateArrowPosition(selectedId);
    }
    });


    // Close report
    $(document).on('click', '.view-report-close', function () {
        $('.main-div').removeClass('hidden')
        $('.report-div').addClass('hidden')
        resetReportData();
    });

    $(document).on('click', '.export-report', function () {
        const $this = $(this)
        $this.prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Exporting...
        `);
        const jobId = $this.attr('data-id')
   $.ajax({
    url: '/ajax/website-export/',
    type: 'POST',
    data: {
        job_id: jobId
    },
    xhrFields: {
        responseType: 'blob'
    },
    success: function (blob, status, xhr) {
        const disposition = xhr.getResponseHeader('Content-Disposition');
        let filename = 'report';

        if (disposition && disposition.indexOf('filename=') !== -1) {
            filename = disposition
                .split('filename=')[1]
                .replace(/"/g, '');
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        $('.main-div').removeClass('hidden')
        $('.report-div').addClass('hidden')
        resetReportData();
        $this.prop('disabled', false).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-download" aria-hidden="true">
            <path d="M12 15V3"></path>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <path d="m7 10 5 5 5-5"></path>
        </svg>
            Download Report
        `);
    },
    error: function () {
        console.error('Export failed');
        $this.prop('disabled', false).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-download" aria-hidden="true">
            <path d="M12 15V3"></path>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <path d="m7 10 5 5 5-5"></path>
        </svg>
            Download Report
        `);
    }
});
    })

    $(document).on('click', '.add-multiple-websites', function () {
      $('#addWebsitesModal').removeClass('hidden');
    document.getElementById('continueBtn').disabled = false;
    });


    $(document).on('click', '#continueBtn', function () {
      handleContinue();
    });


    $(document).on('click', '.close-modal', function () {
      closeModal()
    });

    // Download Report click
    $(document).on('click', '.view-report', function () {
        const $stats = $(this).closest('.verification-list-stats');
        fillReportData($stats);
        $('.main-div').addClass('hidden')
        $('.report-div').removeClass('hidden')
        $('input[name="full_report"][value="yes"]').prop('checked', true)
        $('.export-report').attr('data-id',$stats.attr('data-id'))
    });
    // Radio change
    $('input[name="full_report"]').on('change', function () {
        handleExportOptions($(this).val());
    });

    // Checkbox UI toggle (except disabled)
    $('.export-option').on('click', function () {
        const checkbox = $(this).find('.export-checkbox');
        if (checkbox.prop('disabled')) return;

        checkbox.prop('checked', !checkbox.prop('checked'));
        $(this).find('.check-icon').toggleClass('hidden', !checkbox.prop('checked'));
    });

    // Init on load
    handleExportOptions($('input[name="full_report"]:checked').val());
// startWebsiteStatusPolling();
  });

  function showError(_message) {
    message = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-alert shrink-0" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>' + _message
    $('#uploadError').html(message);
    $('#uploadError').removeClass('hidden');
}

  class ChunkUploader {
    constructor() {
        this.file = null;
        this.max_length = 1024 * 1024 * 10;
    }

    start() {
        const input = document.getElementById('fileInput');
        this.file = input.files[0];
        const oldName = this.file.name;
        this.upload_file(0, null, oldName);
    }

    upload_file(start, model_id, old_file_name) {
        const self = this;
    const uploadSessionPath = model_id;
    const formData = new FormData();

    const nextChunkOffset = start + this.max_length;
    const fileChunk = this.file.slice(start, nextChunkOffset);
    const uploadedBytes = start + fileChunk.size;
    const isLastChunk = uploadedBytes >= this.file.size ? 1 : 0;
    let file_ext = $(this.file.name.split('.')).get(-1)
    let updated_file_name = generateUUID()+'.'+file_ext;
    formData.append('file', fileChunk);
    formData.append('updated_file_name', updated_file_name);
    formData.append('first_row_label', $('input[name="website_first_row_label"]:checked').val());
    formData.append('duplicate_confirm', $('input[name="website_duplicate_confirm"]:checked').val());
    formData.append('selected_file_columns', $('#selected_website_column').val());
    formData.append('original_file_name', old_file_name);
    formData.append('is_last_chunk', isLastChunk);
    formData.append('upload_session_path', uploadSessionPath);
    formData.append('next_chunk_offset', nextChunkOffset);
    formData.append('source', 'website');

    $.ajax({
        xhr: function () {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', function (e) {
                if (!e.lengthComputable) return;

                let percent;

                if (self.file.size <= self.max_length) {
                    percent = Math.round((e.loaded / e.total) * 100);
                } else {
                    const totalUploaded = Math.min(
                        start + e.loaded,
                        self.file.size
                    );
                    percent = Math.round(
                        (totalUploaded / self.file.size) * 100
                    );
                }

                percent = Math.min(percent, 100);

                $('.progress-bar').css('width', percent + '%');
                $('.progress-info').text(percent + '%');
            });

            return xhr;
        },

        url: '/ajax/file-upload/',
        type: 'POST',
        dataType: 'json',
        processData: false,
        contentType: false,
        data: formData,

        success: function (res) {
            if (!res || res.error) {
                showError(res?.error || 'Upload failed. Please try again.');
                return;
            }

            if (nextChunkOffset < self.file.size) {
                self.upload_file(
                    nextChunkOffset,
                    res.upload_session_path,
                    old_file_name
                );
            } else {
                $('.progress-bar').css('width', '100%');
                $('.progress-info').text('100%');
                $('.result-text').text('Finalizing analysis...')
                setTimeout(function () {
                    window.location.reload();
                }, 1500);
            }
        },

        error: function (xhr) {
            showFileError();
        }
    });
    }
}
function fetchData() {
    $.ajax({
        url: `/api/website-validation-list/?page=${currentPage}&status=${currentStatus}`,
        type: "GET",
        success: function (html) {
            $("#websiteListDiv").html(html);
        },
        error: function (xhr) {
            console.error("Error loading HTML:", xhr.responseText);
        },
    });
}

function showFileError(){
    $('.upload-message-text').text('Queueing Interrupted');
    $('.upload-message-div').text('An error occurred during list analysis and preparation. The process has been paused.');
    $('.error-class').addClass('text-red-500');
    $('.tracking-wider.error-class').text('Queue Stopped');
    $('.error-class-progress').addClass('bg-red-50 border-red-100');
    $('.error-class-progress .error-bar').addClass('bg-red-500');
    $('.processing-error-div').removeClass('hidden');
    $('.processing-div').addClass('hidden')
    $('.lucide-search').addClass('text-red-600')
}

function handleExportOptions(value) {
        const $websiteStatus = $('.export-option');
        const $websiteCheckbox = $websiteStatus.find('.export-checkbox');
        const $websiteCheckboxSVG = $websiteStatus.find('svg');
        const $websiteCheckboxText = $websiteStatus.find('.export-checkbox-text');

        if (value === 'no') {
            // Force Website Status checked & disabled
            $websiteCheckbox.prop('disabled', false);
            $websiteCheckboxSVG.attr('stroke','currentColor')

            // $websiteStatus
            //     .addClass('opacity-40 cursor-not-allowed')
            //     .find('.check-icon').removeClass('hidden');
            $websiteCheckboxText.removeClass('opacity-40 cursor-not-allowed')

        } else {
            // Enable everything back
            $websiteCheckbox.prop('checked', true).prop('disabled', true);
            $websiteCheckboxSVG.attr('stroke','#b5b5b8')
            // $websiteStatus.removeClass('opacity-40 cursor-not-allowed');
            $websiteCheckboxText.addClass('opacity-40 cursor-not-allowed')

        $websiteCheckboxSVG.removeClass('hidden');
        }
    }

function parseWebsites(raw) {
    return raw.split(/[\n,;]+/).map(e => e.trim()).filter(e => e.length > 0);
}


function closeModal() {
    document.getElementById('addWebsitesModal').classList.add('hidden');
    document.getElementById('websiteInput').value = '';
    document.getElementById('summary').classList.add('hidden');
}
    function handleContinue() {
      const raw = document.getElementById('websiteInput').value;
      const emptyWarning = document.getElementById('emptyWarning');
      const summary = document.getElementById('summary');
 
      // Step 1: empty check — stop if nothing typed
      if (!raw.trim()) {
        emptyWarning.classList.remove('hidden');
        summary.classList.add('hidden');
        return;
      }
      emptyWarning.classList.add('hidden');
 
      const entries = parseWebsites(raw);
      const seenMap = {};
      const dups    = new Set();
      const valid   = [];
      const invalid = [];
 
      entries.forEach(e => {
        const key = e.toLowerCase();
        seenMap[key] = (seenMap[key] || 0) + 1;
        if (seenMap[key] > 1) dups.add(e);
        if (WEBSITE_REGEX.test(e)) valid.push(e);
        else invalid.push(e);
      });
 
      const uniqueValid = [...new Set(valid.map(e => e.toLowerCase()))];
 
      // Step 2: invalid websites found — show errors and STOP
      if (invalid.length > 0) {
        summary.classList.remove('hidden');
 
        const vb = document.getElementById('validBadge');
        if (uniqueValid.length > 0) {
          vb.textContent = uniqueValid.length + ' valid entry' + (uniqueValid.length !== 1 ? 'ies' : '');
          vb.classList.remove('hidden');
        } else {
          vb.classList.add('hidden');
        }
 
        const ib = document.getElementById('invalidBadge');
        ib.textContent = invalid.length + ' invalid entry' + (invalid.length !== 1 ? 'ies' : '');
        ib.classList.remove('hidden');
 
        const db = document.getElementById('dupBadge');
        if (dups.size > 0) {
          db.textContent = dups.size + ' duplicate entry' + (dups.size !== 1 ? 'ies' : '');
          db.classList.remove('hidden');
        } else {
          db.classList.add('hidden');
        }
 
        const es = document.getElementById('errorSection');
        const ei = document.getElementById('errorItems');
        es.classList.remove('hidden');
        ei.innerHTML = invalid.map(e =>
          `<div class="flex items-center gap-2">
            <span class="font-mono text-base bg-red-50 border border-red-200 text-red-600 px-2 py-0.5 rounded">${escapeHtml(e)}</span>
            <span class="text-base text-gray-400">invalid format</span>
          </div>`
        ).join('');
 
        return; // ← blocked: don't proceed until fixed
      }
 
      // Step 3: all valid — proceed with submission
      // ✅ Replace with your actual submit/API logic
      $('#continueBtn').prop('disabled', true).html(`
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-circle animate-spin" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
            Checking...
        `);
        
    document.getElementById('addWebsitesModal').classList.add('hidden');
        $('.upload-message-text').text('Uploading and Preparing your List...');
    $('.upload-message-div').text('We have queued your list and it will be prepared shortly for validation. You can leave this window and it will redirect you to active lists once analyzing has been finished.');
    $('.error-class').removeClass('text-red-500');
    $('.progress-info.error-class').text('0%');
    $('.progress-bar').css('width', '0%');
    $('.tracking-wider.error-class').text('Analysis Progress');
    $('.error-class-progress').removeClass('bg-red-50 border-red-100');
    $('.error-class-progress .error-bar').removeClass('bg-red-500');
    $('.processing-error-div').addClass('hidden');
    $('.processing-div').removeClass('hidden')
    $('.lucide-search').removeClass('text-red-600')
    $('#listDiv').addClass('hidden');
    $('#statusDiv').addClass('hidden');
    $('#headingDiv').addClass('hidden');
    $('#preparingState').removeClass('hidden');
    $('#previewState').addClass('hidden');

        $.ajax({
            url: '/ajax/process-websites/',
            type: 'POST',
            data: {
                websites: uniqueValid.join(','),
            },
            success: function (res) {
                $('.progress-bar').css('width', '100%');
                $('.progress-info').text('100%');
                $('.result-text').text('Finalizing analysis...')
                setTimeout(function () {
                    window.location.reload();
                }, 1500);
            },
            error: function (xhr) {                showFileError();
            }
        });

    }

function escapeHtml(str) {
    return str.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

// Close modal on backdrop click
document.getElementById('addWebsitesModal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

function initWebsiteSocket() {
    if (websiteSocket) return;

    const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
    websiteSocket = new WebSocket(`${protocol}${location.host}/ws/scraper-dashboard/`);

    websiteSocket.onmessage = (e) => {
        const payload = JSON.parse(e.data);
         const $statsCard = $(
            `.verification-list-stats[data-id="${payload.uuid}"]`
        );
        const status = payload.status
        const credit_balance = Number(payload.credit_balance) || 0
        const credit_reserved = Number(payload.credit_reserved) || 0

        if (payload.credit_balance != null) {
            $('.available-balance').text(credit_balance)
            $('.credit-reserved').text(credit_reserved)
            $('.credit-balance').text(credit_balance + credit_reserved)
        }

        if (!$statsCard.length) return;

        updateStatsCard($statsCard, payload);
        updateListStatus(payload.uuid, status);
        updateStatsStatus($statsCard, payload.status)
        if (status === STATUS.PROCESSING) {
            updateProgress(
                payload.uuid,
                payload.completed_count || 0,
                payload.total_items || 0
            );
        }

        // Optional: handle completion timestamp
        if (status === STATUS.COMPLETED && payload.completed_at) {
            const $list = $(`.verification-list[data-id="${payload.uuid}"]`);
            $list.find('.list-status-completed-div')
                .html(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check text-green-500" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>Finished at ${payload.completed_at}`);
        }
        updateDonutChart(payload.uuid, {
        valid: payload.valid_count,
        invalid: payload.invalid_count,
        unknown: payload.unknown_count,
        total: payload.total_items
    });
    };
}

function updateJobUI(job) {
    const $card = $(`.verification-list[data-id="${job.uuid}"]`);
    if (!$card.length) return;

    const percent = Math.round((job.completed / job.total) * 100);

    $card.find('.progress-bar').css('width', `${percent}%`);
    $card.find('.stats-valid').text(job.valid);
    $card.find('.stats-invalid').text(job.invalid);

    if (job.done) {
        $card.addClass('border-green-500');
        $card.find('.status-text').text('Completed');
    }
}

function generateUUID() {
    var d = new Date().getTime();
    var uuid = 'xxxxxxxx-xxxx-yxxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
     return uuid;
};
function detectWebsiteColumns(headers, rows) {
    const columnStats = {};
    const sampleSize = Math.min(rows.length, 30);

    headers.forEach((_, colIndex) => {
        columnStats[colIndex] = {
            total: 0,
            matches: 0,
            nonEmpty: 0,
            uniqueDomains: new Set()
        };
    });

    const normalizeWebsite = (val) => {
        if (!val || typeof val !== 'string') return null;

        let v = val.trim().toLowerCase();

        // Remove protocol
        v = v.replace(/^https?:\/\//, '');

        // Remove www
        v = v.replace(/^www\./, '');

        // Remove path/query
        v = v.split('/')[0];

        return v;
    };

    const isValidDomain = (domain) => {
        if (!domain) return false;

        // Reject obvious non-domains
        if (domain.includes(' ') || !domain.includes('.')) return false;

        // Basic domain regex
        return /^[a-z0-9.-]+\.[a-z]{2,}$/.test(domain);
    };

    for (let i = 0; i < sampleSize; i++) {
        const row = rows[i];

        headers.forEach((_, colIndex) => {
            const rawValue = row[colIndex];
            const value = normalizeWebsite(rawValue);

            columnStats[colIndex].total++;

            if (value) {
                columnStats[colIndex].nonEmpty++;

                if (isValidDomain(value)) {
                    columnStats[colIndex].matches++;
                    columnStats[colIndex].uniqueDomains.add(value);
                }
            }
        });
    }

    return headers
        .map((header, index) => {
            const stat = columnStats[index];

            if (stat.nonEmpty === 0) return null;

            const ratio = stat.matches / stat.nonEmpty;

            // Additional signal: diversity of domains
            const diversity = stat.uniqueDomains.size;

            // Heuristic scoring
            if (
                stat.matches >= 3 &&
                ratio >= 0.4 &&
                diversity >= 2 // avoids repeated junk values
            ) {
                return {
                    index,
                    header,
                    confidence: ratio.toFixed(2),
                    uniqueDomains: diversity
                };
            }

            return null;
        })
        .filter(Boolean);
}
function renderPreview(headers, rows, previewLimit = 5) {
    let detectedWebsiteIndex = -1;
    const sampleRows = rows.slice(0, previewLimit);

    const normalizeWebsite = (val) => {
        if (!val || typeof val !== 'string') return null;

        let v = val.trim().toLowerCase();

        // remove protocol
        v = v.replace(/^https?:\/\//, '');

        // remove www
        v = v.replace(/^www\./, '');

        // remove path/query
        v = v.split('/')[0];

        return v;
    };

    const isValidDomain = (domain) => {
        if (!domain) return false;

        // reject emails
        if (domain.includes('@')) return false;

        // must contain dot + valid tld
        return /^[a-z0-9.-]+\.[a-z]{2,}$/.test(domain);
    };

    // 🔍 Detect best website column
    let bestScore = 0;

    headers.forEach((header, colIndex) => {
        let matches = 0;
        let nonEmpty = 0;

        sampleRows.forEach(row => {
            const raw = row[colIndex];
            const value = normalizeWebsite(raw);

            if (value) {
                nonEmpty++;

                if (isValidDomain(value)) {
                    matches++;
                }
            }
        });

        if (nonEmpty === 0) return;

        const ratio = matches / nonEmpty;

        // header boost
        const headerBoost = /website|domain|url|site/i.test(header) ? 0.2 : 0;

        const score = ratio + headerBoost;

        if (matches >= 2 && score > bestScore) {
            bestScore = score;
            detectedWebsiteIndex = colIndex;
            selectedWebsiteColumns.add(colIndex);
        }
    });

    // ================= UI RENDER =================

    let theadHtml = '<tr class="bg-gray-50/50">';
    headers.forEach((header, index) => {
        const isWebsite = index === detectedWebsiteIndex;

        theadHtml += `
        <th class="p-4 border-b border-gray-100 text-left">
            <div class="flex flex-col gap-3">
                <div data-index="${index}" class="flex items-center justify-center px-3 py-2 rounded-lg border transition-all column-selector
                    ${isWebsite
                        ? 'bg-primary border-primary text-white shadow-md shadow-primary/20'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'}">
                    <span class="text-xs font-bold uppercase tracking-wider truncate pr-2">
                        ${isWebsite ? 'Website Address' : 'Ignore Column'}
                    </span>
                    <div class="w-4 h-4 rounded-full flex items-center justify-center border transition-all header-tick
                        ${isWebsite
                            ? 'bg-white border-white'
                            : 'bg-transparent border-gray-300'}">
                        ${isWebsite
                            ? `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"
                                viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="4" stroke-linecap="round"
                                stroke-linejoin="round"
                                class="lucide lucide-check text-primary">
                                <path d="M20 6 9 17l-5-5"></path>
                               </svg>`
                            : ''}
                    </div>
                </div>
            </div>
        </th>`;
    });
    theadHtml += '</tr>';

    let tbodyHtml = '';

    // Header row (strikethrough)
    tbodyHtml += '<tr class="border-b border-gray-50/50">';
    headers.forEach(h => {
        tbodyHtml += `
        <td class="p-4">
            <div class="text-sm truncate max-w-[200px] text-gray-300 italic line-through">
                ${h}
            </div>
        </td>`;
    });
    tbodyHtml += '</tr>';

    // Data rows
    rows.slice(0, previewLimit).forEach(row => {
        tbodyHtml += '<tr class="border-b border-gray-50/50 hover:bg-gray-50/30 transition-colors">';
        row.forEach((cell, index) => {
            tbodyHtml += `
            <td class="p-4">
                <div class="text-sm truncate max-w-[200px]
                    ${index === detectedWebsiteIndex
                        ? 'text-gray-900 font-bold'
                        : 'text-gray-500 font-medium'}">
                    ${cell || ''}
                </div>
            </td>`;
        });
        tbodyHtml += '</tr>';
    });

    $('#previewTable thead').html(theadHtml);
    $('#previewTable tbody').html(tbodyHtml);

    // Persist selection
    if (detectedWebsiteIndex !== -1) {
        $('#selected_website_column').val(detectedWebsiteIndex);
        $('.validate-websites').removeAttr('disabled');
    } else {
        $('.validate-websites').attr('disabled', true);
    }
}



function updateArrowPosition(selectedId) {
    const $activeItem = $('[data-id="' + selectedId + '"]');
    const $container = $('#listDiv');
    const $arrow = $('#arrowBtn');

    if (!$activeItem.length || !$container.length || !$arrow.length) return;

    const containerHeight = $container.innerHeight();
    const arrowHeight = $arrow.outerHeight();

    // Center of active item relative to container
    let itemCenterOffset =
        $activeItem.position().top + ($activeItem.outerHeight() / 2);

    // Adjust based on scroll
    let relativeToScroll = itemCenterOffset - $container.scrollTop();

    // 🔒 CLAMP within visible area (no above scrollbar)
    const minTop = 0;
    const maxTop = containerHeight - arrowHeight;

    relativeToScroll = Math.max(minTop, Math.min(relativeToScroll, maxTop));

    // Apply position
    if (relativeToScroll < 20){
        relativeToScroll = 20
    }
    $arrow.css('top', relativeToScroll + 30 + 'px');
    if (relativeToScroll == 20){
        $arrow.find('svg').css('transform', 'rotate(90deg)');

    }
    else{

        $arrow.find('svg').css('transform', 'rotate(0deg)');
    }
}

function updateHiddenInput() {
    $('#selected_website_columns').val([...selectedWebsiteColumns].join(','));
    
    if ([...selectedWebsiteColumns].length !== 0) {
        $('.validate-websites').removeAttr('disabled')
    }
    else{
        $('.validate-websites').attr('disabled',true)
    }
}
function updateHeaderUI() {
    $('.column-selector').each(function () {
        const $el = $(this);
        const index = $el.data('index');
        const isWebsite = selectedWebsiteColumns.has(index);

        // Label
        $el.find('span').text(
            isWebsite ? 'Website Address' : 'Ignore Column'
        );
        $el.find('span').addClass(
            isWebsite ? '' : 'text-gray-400'
        );
        $el.find('div.header-tick').addClass(
            isWebsite ? '' : 'hidden'
        );

        // Container styles
        $el
            .toggleClass(
                'bg-primary border-primary text-white shadow-md shadow-primary/20',
                isWebsite
            )
            .toggleClass(
                'bg-white border-gray-200 text-gray-600 hover:border-gray-300',
                !isWebsite
            );

        // Check icon circle
        const $icon = $el.find('.w-4.h-4');
        $icon
            .toggleClass('bg-white border-white', isWebsite)
            .toggleClass('bg-transparent border-gray-300', !isWebsite)
            .html(isWebsite ? CHECK_ICON_SVG : '');
    });
}
function updateStatsCard($card, data) {
    // Update data-status
    $card.attr('data-status', data.status);

    // -------- BASIC INFO --------
    $card.find('.stats-name').text(data.name);
    $card.find('.stats-records').text(data.total_items);
    $card.find('.stats-format').text(data.source_format);

    // -------- STATUS TEXT --------
    updateStatsStatus($card, data.status);

    // -------- COUNTS --------
    $card.find('.stats-valid').text(data.valid_count);
    $card.find('.stats-invalid').text(data.invalid_count);
    $card.find('.stats-risky').text(data.risky_count);
    $card.find('.stats-unknown').text(data.unknown_count);
    $card.find('.stats-role').text(data.role_based_count);
    $card.find('.stats-disposable').text(data.disposable_count);
    $card.find('.stats-catch-all').text(data.catch_all_count);
    $card.find('.stats-duplicate').text(data.total_duplicate);
    left_count = data.total_items - data.completed_count
    $card.find('.error-count').text(`You will pay ${left_count} credits for this validation.`)

    // -------- COMPLETION TIME --------
    if (data.status === 5 && data.completed_at) {
        $card.find('.stats-status-completed-text')
            .removeClass('hidden')
            .html(formatCompletedAt(data.completed_at));
        $card.find('.download-button')
            .removeClass('hidden')
            
    }
}
function updateStatsStatus($card, status) {
    $card.find(`
        .stats-status-ready,
        .stats-status-failed,
        .stats-status-processing,
        .stats-status-completed,
        .stats-status-completed-div,
        .stats-status-completed-text
    `).addClass('hidden');


    if (status === 3) {
        // IN PROGRESS
        $card.find(`
        .stats-status-processing
        `).removeClass('hidden');
    }
    else if (status === 5) {
        // COMPLETED
        $card.find(`
        .stats-status-completed
        `).removeClass('hidden');
        $card.find(`
        .stats-status-completed-div
        `).removeClass('hidden');
        $card.find(`
        .stats-status-completed-text
        `).removeClass('hidden');
    }
    else if (status === 4) {
        // FAILED
        $card.find(`
        .stats-status-failed
        `).removeClass('hidden');
         $card.find(`
        .stats-status-failed-div
        `).removeClass('hidden');
    }
}
function formatCompletedAt(dateStr) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check text-green-500" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>Finished at ${dateStr}`
}


function startWebsiteStatusPolling() {
    if (websitePollingInterval) return;

    websitePollingInterval = setInterval(function () {
        const jobIds = collectInProgressJobIds();

        // Nothing to poll → stop
        if (!jobIds.length) {
            stopWebsiteStatusPolling();
            return;
        }

        fetchWebsiteJobStatuses(jobIds);
    }, POLL_INTERVAL);
}

function stopWebsiteStatusPolling() {
    clearInterval(websitePollingInterval);
    websitePollingInterval = null;
    console.log('Website polling stopped');
}

function collectInProgressJobIds() {
    const ids = [];

    $('.verification-list').each(function () {
        const status = parseInt($(this).data('status'), 10);
        if (status === INPROGRESS) {
            ids.push($(this).data('id'));
        }
    });

    return ids;
}
function handleWebsiteStatsResponse(apiResponse) {
    if (!apiResponse || !apiResponse.response) return;

    apiResponse.response.forEach(job => {
        const $statsCard = $(
            `.verification-list-stats[data-id="${job.uuid}"]`
        );

        if (!$statsCard.length) return;

        updateStatsCard($statsCard, job);
    });
}

function fetchWebsiteJobStatuses(jobIds) {
    $.ajax({
        url: '/api/website-validation/',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ job_ids: jobIds }),
        success: function (response) {
            handleWebsiteStatsResponse(response);
        stopIfAllCompleted();
        },
        error: function () {
            console.error('Website status fetch failed');
        }
    });
}
function stopIfAllCompleted() {
    let hasInProgress = false;

    $('.verification-list').each(function () {
        if (parseInt($(this).data('status'), 10) === INPROGRESS) {
            hasInProgress = true;
            return false;
        }
    });

    if (!hasInProgress) {
        stopWebsiteStatusPolling();
    }
}
function updateListStatus(uploadId, status) {
    const $list = $(`.verification-list[data-id="${uploadId}"]`);

    // Hide everything first
    $list.find(`
        .list-status-ready,
        .list-status-processing,
        .list-status-completed,
        .list-status-failed,
        .list-status-processing-div,
        .list-status-completed-div,
        .list-status-failed-div
    `).addClass('hidden');

    switch (status) {
        case STATUS.READY:
            $list.find('.list-status-ready').removeClass('hidden');
            break;

        case STATUS.PROCESSING:
            $list.find('.list-status-processing').removeClass('hidden');
            $list.find('.list-status-processing-div').removeClass('hidden');
            break;

        case STATUS.COMPLETED:
            $list.find('.list-status-completed').removeClass('hidden');
            $list.find('.list-status-completed-div').removeClass('hidden');
            break;

        case STATUS.FAILED:
            $list.find('.list-status-failed').removeClass('hidden');
            $list.find('.list-status-failed-div').removeClass('hidden');
            break;
    }

    $list.attr('data-status', status);
}
function updateProgress(uploadId, processed, total) {
    const percent = total > 0 ? Math.round((processed / total) * 100) : 0;

    const $list = $(`.verification-list[data-id="${uploadId}"]`);

    $list.find('.ongoing-stats-data')
        .text(`Validating ${percent}%`);

    $list.find('.ongoing-stats-count')
        .text(`${processed}/${total}`);

    $list.find('.ongoing-stats-width')
        .css('width', `${percent}%`);
}

function fillReportData($stats) {
        const map = {
            '.stats-name': '.report-name',
            '.stats-records': '.report-record',
            '.stats-format': '.report-format',
            '.stats-status-completed-text': '.report-complete',
            '.stats-valid': '.report-valid',
            '.stats-invalid': '.report-invalid',
            '.stats-risky': '.report-risky',
            '.stats-unknown': '.report-unknown',
            '.stats-catch-all': '.report-catch-all',
            '.stats-role': '.report-role',
            '.stats-disposable': '.report-disposable',
            '.stats-duplicate': '.report-duplicate'
        };

        $.each(map, function (from, to) {
            const value = $stats.find(from).first().html() || '';
            $(to).html(value);
        });

        $('.report-div').removeClass('hidden');
    }

    function resetReportData() {
        const reportFields = [
            '.report-name',
            '.report-record',
            '.report-format',
            '.report-complete',
            '.report-valid',
            '.report-invalid',
            '.report-risky',
            '.report-unknown',
            '.report-catch-all',
            '.report-role',
            '.report-disposable',
            '.report-duplicate'
        ];

        reportFields.forEach(selector => {
            $(selector).html('');
        });

        $('.report-div').addClass('hidden');
    }

function setSegment(job_id, id, length, offset) {
  const $container = $(`.verification-list-stats[data-id="${job_id}"]`);
  const $el = $container.find(`#${id}`);

  if (!$el.length) return;

  $el.attr(
    "stroke-dasharray",
    `${length} ${CIRCUMFERENCE}`
  );

  $el.attr(
    "stroke-dashoffset",
    `-${offset}`
  );
}


  function updateDonutChart(job_id, stats) {
    const total = stats.total;


    $(`.verification-list-stats[data-id="${job_id}"]`).find('.delivery-perc').text(((stats.valid/total)*100).toFixed(1) + '%');

    let offset = 0;

    const segments = [
      { id: "seg-valid", value: stats.valid },
      { id: "seg-invalid", value: stats.invalid },
      { id: "seg-unknown", value: stats.unknown },
    ];

    segments.forEach(seg => {
      const length = (seg.value / total) * CIRCUMFERENCE;
      setSegment(job_id, seg.id, length, offset);
      offset += length;
    });
  }








