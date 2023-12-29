$(document).ready(function() {
    $(document).on("click", '.vertical-menu-filter',function(e){e.preventDefault();
    $('body').toggleClass("sidebar-enable");
    })
    $('select[name="industry_keyword"]').select2({
        tags: true
      })

    $(document).on('click', '.agree-access', function(){
        $('#accessInfoModal .credit-buy').addClass('d-none')
        $('#accessInfoModal .agree-access-submit').removeClass('d-none')
        sessionStorage.setItem('access_id', $(this).attr('data-access'));
        sessionStorage.setItem('listing', $(this).data('listing'));
        sessionStorage.setItem('box-id', $(".search-results .data-box-result").index($(this).closest(".data-box-result")));
        $.get('/accounts/credit-status/', function(response){
            $('#accessInfoModal .access-credit').html(response.data)
            if(parseInt(response.data) < 1 ){
                $('#accessInfoModal .has-credit').addClass('d-none')
                $('#accessInfoModal .credit-buy').removeClass('d-none')
                $('#accessInfoModal .agree-access-submit').addClass('d-none')
                
            }
            $('#accessInfoModal').modal('show');
        })

    })
    $(document).on('click', '.agree-access-submit', function(event){
        event.preventDefault();
        var self = $(this)
        var data = self.closest('form').serializeArray()
        data.push({name: "access_id", value: sessionStorage.getItem('access_id')});
        data.push({name: "listing", value: sessionStorage.getItem('listing')});
 
    $.ajax({
        type: 'POST',
        url: '/app/credit-access/',
        data: $.param(data),
        success: function(response) {
            if (response.success) {
                
                $(".search-results .data-box-result").eq(sessionStorage.getItem('box-id')).replaceWith(response.data)
                feather.replace()
                sessionStorage.clear();
            }
            $('#accessInfoModal').modal('hide');
        }}
        )
    })
     
})