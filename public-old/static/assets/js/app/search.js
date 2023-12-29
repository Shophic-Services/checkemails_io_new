var retrievedData = localStorage.getItem("search_update_data");
var search_update_data = JSON.parse(retrievedData);

var updated = []
var pageActionType = null;

if(!search_update_data){
	search_update_data = []
}

$(window).on('load',function(){
    // $('.page-custom-total').val('1');
    // localStorage.setItem("search_update_data", JSON.stringify([]));
    retrievedData = localStorage.getItem("search_update_data");
    clear_filter_data($('#side-menu'))
})

$(document).ready(function() {

    $(document).on('click', '.page-item',function(){
        var self = $(this)
        self.closest('.pagination').find('.page-item.active').removeClass('active');
        self.addClass('active');
        self.closest('.pagination').attr('data-current', self.find('.page-link').attr('data-page'));
        pageActionType = 'pagination';
        ajax_send();
    })
    $(document).on('click','.result-listing-li', function(){
        $(this).closest('.result-listing-head').find('.result-listing-li').removeClass('active').find('.nav-link').removeClass('active')
        $(this).find('input').prop('checked', true)
        $(this).closest('.result-listing-li').addClass('active').find('.nav-link').addClass('active')
        pageActionType = 'listing';
        ajax_send();
    })
    
    // $(document).on('click','.result-type-li', function(){
    //     $(this).closest('.result-type-head').find('.result-type-li').removeClass('active').find('.nav-link').removeClass('active')
    //     // $(this).find('input').prop('checked', true)
    //     $(this).closest('.result-type-li').addClass('active').find('.nav-link').addClass('active')
    //     pageActionType = 'type';
    //     $('.result-listing:first').prop('checked',true)
    //     $('.result-listing:first').closest('.result-listing-head').find('.result-listing-li').removeClass('active').find('.nav-link').removeClass('active')
    //     $(this).find('input').prop('checked', true)
    //     $('.result-listing:first').closest('.result-listing-li').addClass('active').find('.nav-link').addClass('active')
    //     // $('div.search-field input').val('')
    //     ajax_send();
    // })

    $(document).on('click', '.search-record', function(){
        pageActionType = 'search';
        ajax_send();

    });

    $(document).on('keyup', 'div.search-field input', function(event){
        pageActionType = 'search';
        if (event.key === 'Enter') {
            ajax_send();
        }
    });

    

    $(document).on('keyup', 'input.filter-input', function(event){
        if (event.key === 'Enter') {
            pageActionType = 'search';
        
        ajax_send();
        }
    });
    $('.filter-clear').on('click',function(){
        pageActionType = 'filter';
        clear_filter_data($('#side-menu'))
        retrievedData = []
        ajax_send();
    });

    

})

function clear_filter_data(class_instance){

    class_instance.find('.nav-item').each(function(){
        $(this).find('input').val('');
    })
}

function get_filter_data(class_instance){

    var filter_set = new Object();
    updated = []
    class_instance.find('li input').each(function(){
        var self = $(this)
        filter_set[self.attr('name')] = self.val()
    })
    filter_set['listing'] = $('input.result-listing:checked').val()
    filter_set['search'] = $('div.search-field input').val()
    filter_set['type'] = $('input.result-type:checked').val()
    filter_set['page'] = $('.pagination').attr('data-current');
    localStorage.setItem("search_update_data", JSON.stringify(filter_set));
    retrievedData = localStorage.getItem("search_update_data");
    
}

function get_filter_data_update(data){

    $.each(data, function( name, value ) {
        $('.filter-type[data-type="' + name + '"]').closest('.data-row').find('.filter-type-list input').each(function(){
            if ($(this).is(':checkbox')){
                if(jQuery.inArray($(this).attr('data-id'), value) !== -1){
                    $(this).attr('checked', true).prop('checked', true)
                }
                else{
                    $(this).removeAttr('checked').prop('checked', false)
                }
            }
        })
    })
    
}

function ajax_send(){

    $('div#loader').removeClass('fadeOut')
    get_filter_data($('#side-menu'));
    search_update_data = JSON.parse(retrievedData);
    search_update_data['page_action_type'] = pageActionType;
    $.ajax({
        url: window.location.pathname + '?' + 'search_update_data=' + JSON.stringify(search_update_data),
        success: function(response) {
            $( ".search-results" ).html( response );
            feather.replace()
            setTimeout(function () {$('div#loader').addClass('fadeOut');}, 100);
        },
        error: function(error) {
            console.log('Something went wrong');
            alert('Something went wrong');
        }
    });
    
}
