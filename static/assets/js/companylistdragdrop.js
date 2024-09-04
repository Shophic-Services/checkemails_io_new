class FileUpload {

    constructor(input) {
        this.input = input
        this.max_length = 1024 * 1024 * 10;
    }

    create_progress_bar() {
        var progress = `
        <div class="data-list-inner">
					<div class="data-list-left">
						<div class="icon-sec">
							<i class="far fa-file"></i>
						</div>
						<div class="data-content">
							<h4 class="filename"></h4>
                            <p class="data-content-div"><i class="far fa-clock"></i> - </p>
						</div>
					</div>
                    <div class="w-100 validation-info position-relative">
                            <p class="m-0"><small class="textbox"></small></p>
                            <div class="progress-info">
                                <h6 class="m-0">0%</h6>
                                <span class="remaining"></span>
                            </div>
                            <p>
                            <div class="progress" style="margin-top: 5px;">
                                <div class="progress-bar bg-success" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 0%">
                                </div>
                            </div>
                            </p>
                        </div>
				</div>
        `
        document.getElementById('uploaded_files').innerHTML = progress
    }

    upload() {
        this.create_progress_bar();
        this.initFileUpload();
    }

    initFileUpload() {
        this.file = this.input.files[0];
        let old_file_name = this.file.name
        let file_ext = $(this.file.name.split('.')).get(-1)
        let new_file = new File([this.file], generateUUID()+'.'+file_ext, {type: this.file.type});
        
        this.file = new_file;
        this.upload_file(0, null, old_file_name);

    }

    //upload file
    upload_file(start, model_id, old_file_name) {
        var end;
        var self = this;
        var existing_path = model_id;
        var form_data = new FormData();
        var next_chunk = start + this.max_length + 1;
        var current_chunk = this.file.slice(start, next_chunk);
        var uploaded_chunk = start + current_chunk.size
        if (uploaded_chunk >= this.file.size) {
            end = 1;
        } else {
            end = 0;
        }
        form_data.append('file', current_chunk)
        form_data.append('updated_file_name', this.file.name)
        form_data.append('file_name', old_file_name)
        $('.filename').text(old_file_name)
        $('.textbox').text("Uploading file")
        form_data.append('end', end)
        form_data.append('existing_path', existing_path);
        form_data.append('next_slice', next_chunk);
        let remaining = document.querySelector(".remaining");
        $.ajaxSetup({
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        });
        $.ajax({
            xhr: function () {
                var xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', function (e) {
                    if (e.lengthComputable) {
                        if (self.file.size < self.max_length) {
                            var percent = Math.round((e.loaded / e.total) * 100);
                        } else {
                            var percent = Math.round((uploaded_chunk / self.file.size) * 100);
                        }
                        $('.progress-bar').css('width', percent + '%')
                        remaining.textContent =
                            "remaining " + Math.round(self.file.size / uploaded_chunk) + "s";
                            if (percent >= 100) {
                            remaining.textContent = "";
                            }
                            $('.progress-info').html(percent + '%')
                    }
                });
                return xhr;
            },

            url: '/check/bulk-process-email-list/',
            type: 'POST',
            dataType: 'json',
            cache: false,
            processData: false,
            contentType: false,
            data: form_data,
            error: function (xhr) {
                $('.validation-info').html(`
                <ul class="data-validation">
                <li><p class="text-black">Total Emails</p><span class="red">-</span></li>
                <li><p class="text-black">Valid</p><span class="green">-</span></li>
                <li class="ps-2 me-3"><p class="text-black">Status</p><span class="grey"><span class="status-pill-button status-pill-button-4">Error</span></span></li>
                
            </ul>
                    `);
                    $('#uploaded_files .validation-info').removeClass('validation-info');
                    $('.no-data-found').addClass('d-none')
                
            },
            success: function (res) {
                if (next_chunk < self.file.size) {
                    // upload file in chunks
                    existing_path = res.existing_path
                    self.upload_file(next_chunk, existing_path);
                } else {
                    // upload complete
                    $('.textbox').text(res.data);
                    setTimeout(function () { 
                    $('.validation-info').closest('#uploaded_files').find('.data-content-div').html(`
                    <p><i class="far fa-clock"></i> `+ res.date +` </p>
                    `)
                    $('.validation-info').html(`
                    <ul class="data-validation">
						<li><p class="text-black">Total Emails</p><span class="red">-</span></li>
						<li><p class="text-black">Valid</p><span class="green">-</span></li>
						<li class="ps-2 me-3"><p class="text-black">Status</p><span class="grey"><span class="status-pill-button status-pill-button-1">Pending</span></span></li>
					</ul>
                    `);
                    $('#uploaded_files .validation-info').removeClass('validation-info');
                    $('.no-data-found').addClass('d-none')
                }, 1000);
                $.ajax({
                    url: '/check/bulk-process-email-list/'+ res.uuid + '/',
                    type: 'GET',
                    dataType: 'json',
                    cache: false,
                    processData: false,
                    contentType: false,
                    error: function (xhr) {
                        alert(xhr.statusText);
                    },
                    success: function (res) {
                        window.location.reload()
                    }
                });
                }
            }
        });

        
    };
}

(function ($) {

    $('#fileupload_button').on('click', (event) => {
        event.preventDefault();
        $('#fileupload').click();
    });
    $('#fileupload').on('change', function(){
        var uploader = new FileUpload(document.querySelector('#fileupload'))
        uploader.upload();
    })
})(jQuery);

ondragenter = function(evt) {
    evt.preventDefault();
    evt.stopPropagation();
};

ondragover = function(evt) {
    evt.preventDefault();
    evt.stopPropagation();
};

ondragleave = function(evt) {
    evt.preventDefault();
    evt.stopPropagation();
};
  
ondrop = function(evt) {
    evt.preventDefault();
    evt.stopPropagation();
    const files = evt.originalEvent.dataTransfer;
    var uploader = new FileUpload(files);
    uploader.upload();
};

$('#dropBox')
    .on('dragover', ondragover)
    .on('dragenter', ondragenter)
    .on('dragleave', ondragleave)
    .on('drop', ondrop);


function generateUUID() {
    var d = new Date().getTime();
    var uuid = 'xxxxxxxx-xxxx-yxxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
     return uuid;
    };